from __future__ import annotations

import logging
import re
from collections import OrderedDict

from app.domain.enums import normalize_kocaeli_district

from ..ner.normalizer import normalize_location_text
from ..ner.schemas import NERResult
from .cache import RedisGeoCache
from .config import GeocodingConfig
from .exceptions import ProviderRateLimitError, ProviderUnavailableError
from .metrics import GeocodingMetrics
from .providers.base import GeocodingProvider
from .queue import GeocodingQueue
from .schemas import (
    GeocodingFailure,
    GeocodingInput,
    GeocodingResult,
    _normalize_for_compare,
)

logger = logging.getLogger(__name__)

_LAT_MIN, _LAT_MAX = 40.35, 41.15
_LNG_MIN, _LNG_MAX = 29.10, 30.90
_MAX_LOCATION_CANDIDATES = 8
_GENERIC_LOCATION_TOKENS = {
    "belediyesi",
    "belediye",
    "buyuksehir belediyesi",
    "valilik",
    "kaymakamligi",
    "mudurlugu",
    "genel mudurlugu",
    "bakanligi",
}
_GENERIC_LOCATION_HARD_SUFFIXES = (
    "bankasi",
    "belediyesi",
    "universitesi",
    "mahkemesi",
    "mudurlugu",
    "bakanligi",
    "kaymakamligi",
    "valiligi",
)
_GENERIC_LOCATION_SOFT_SUFFIXES = (
    "cezaevi",
    "hastanesi",
)
_GENERIC_TEAM_ALIASES = (
    "kocaelispor",
    "gebzespor",
    "karamurselspor",
    "darica genclerbirligi",
    "darica gb",
)

KOCAELI_DISTRICTS = frozenset(
    _normalize_for_compare(name)
    for name in (
        "Izmit",
        "Gebze",
        "Darica",
        "Golcuk",
        "Hereke",
        "Korfez",
        "Kartepe",
        "Basiskele",
        "Cayirova",
        "Dilovasi",
        "Kandira",
        "Karamursel",
        "Derince",
    )
)

_PRECISE_LOCATION_HINTS = (
    "mahallesi",
    "mahalle",
    "sokak",
    "cadde",
    "caddesi",
    "bulvar",
    "blv",
    "baraji",
    "goleti",
    "tesisi",
    "aritma tesisi",
    "aritma",
    "icmesuyu",
    "isale",
    "iletim",
    "tuneli",
    "liman",
    "hastanesi",
    "cezaevi",
    "stadyumu",
    "kampusu",
    "terminali",
    "kavsagi",
    "meydani",
)

_INVALID_NEIGHBORHOOD_PREFIX_TOKENS = (
    "mahallesi",
    "mahalle",
    "sokak",
    "cadde",
    "caddesi",
    "bulvar",
    "blv",
)
_USE_NER_FALLBACK = object()


class GeocodingService:
    def __init__(
        self,
        provider: GeocodingProvider,
        cache: RedisGeoCache,
        queue: GeocodingQueue,
        metrics: GeocodingMetrics,
        config: GeocodingConfig,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._queue = queue
        self._metrics = metrics
        self._cfg = config

    def geocode(
        self,
        input_data: GeocodingInput,
    ) -> GeocodingResult | GeocodingFailure:
        cached = self._cache.get(input_data)
        if cached:
            self._metrics.record_success(
                source="cache",
                district=cached.district,
                confidence=cached.confidence,
            )
            return cached

        try:
            result = self._provider.geocode(input_data)
        except ProviderRateLimitError as exc:
            self._metrics.record_rate_limit(
                exc.provider,
                exc.retry_after,
                address=input_data.address,
            )
            queued = self._queue.enqueue(
                input_data,
                reason=f"rate_limit:{exc.provider}",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"{exc.provider} rate limit",
                failure_type="rate_limit" if queued else "queue_full",
                news_id=input_data.news_id,
            )
        except ProviderUnavailableError as exc:
            self._metrics.record_failure(
                input_data.address,
                "provider_error",
                str(exc),
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=str(exc),
                failure_type="provider_error",
                news_id=input_data.news_id,
            )
        except Exception as exc:
            self._metrics.record_failure(
                input_data.address,
                "provider_error",
                f"{type(exc).__name__}: {exc}",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"{type(exc).__name__}: {exc}",
                failure_type="provider_error",
                news_id=input_data.news_id,
            )

        if result is None:
            self._metrics.record_failure(
                input_data.address,
                "not_found",
                "No geocoding result",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason="No geocoding result",
                failure_type="not_found",
                news_id=input_data.news_id,
            )

        if not self._in_kocaeli_bounds(result.lat, result.lng):
            self._metrics.record_failure(
                input_data.address,
                "out_of_bounds",
                result.display_name,
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=result.display_name,
                failure_type="out_of_bounds",
                news_id=input_data.news_id,
            )

        if result.confidence < self._cfg.min_confidence:
            self._metrics.record_failure(
                input_data.address,
                "low_confidence",
                f"{result.confidence:.3f} < {self._cfg.min_confidence:.3f}",
            )
            return GeocodingFailure(
                address=input_data.address,
                reason=f"Low confidence: {result.confidence:.3f}",
                failure_type="low_confidence",
                news_id=input_data.news_id,
            )

        self._cache.set(input_data, result)
        self._metrics.record_success(
            source=result.source,
            district=result.district,
            confidence=result.confidence,
        )
        return result

    def metrics_summary(self) -> dict:
        summary = self._metrics.summary()
        summary["cache_available"] = self._cache.available
        summary["queue_size"] = self._queue.size
        summary["provider"] = self._provider.name
        return summary

    @staticmethod
    def _in_kocaeli_bounds(lat: float, lng: float) -> bool:
        return _LAT_MIN <= lat <= _LAT_MAX and _LNG_MIN <= lng <= _LNG_MAX


def build_geocoding_input_from_ner(
    ner_result: NERResult,
    news_id: str | None = None,
    fallback_district: str | None | object = _USE_NER_FALLBACK,
) -> GeocodingInput | None:
    inputs = build_geocoding_inputs_from_ner(
        ner_result,
        news_id=news_id,
        fallback_district=fallback_district,
    )
    return inputs[0] if inputs else None


def build_geocoding_inputs_from_ner(
    ner_result: NERResult,
    news_id: str | None = None,
    fallback_district: str | None | object = _USE_NER_FALLBACK,
) -> list[GeocodingInput]:
    if not ner_result.location_candidates and not ner_result.validated_districts:
        return []

    deduped: OrderedDict[tuple[str, str | None], GeocodingInput] = OrderedDict()

    def add_input(
        *,
        address: str | None,
        district_hint: str | None = None,
        neighborhood: str | None = None,
    ) -> None:
        if address is None:
            return

        clean_address = address.strip()
        clean_district = district_hint.strip() if district_hint else None
        clean_neighborhood = _clean_location_value(neighborhood)
        if not clean_address:
            return

        key = (
            _normalize_for_compare(clean_address),
            _normalize_for_compare(clean_district) if clean_district else None,
        )
        if key in deduped:
            return

        deduped[key] = GeocodingInput(
            address=clean_address,
            district_hint=clean_district,
            neighborhood=clean_neighborhood,
            news_id=news_id,
        )

    if fallback_district is _USE_NER_FALLBACK:
        resolved_fallback_district = next(
            (
                candidate.district
                for candidate in ner_result.location_candidates
                if candidate.district
            ),
            None,
        ) or (
            ner_result.validated_districts[0]
            if ner_result.validated_districts
            else None
        )
    else:
        resolved_fallback_district = fallback_district

    for candidate in ner_result.location_candidates[:_MAX_LOCATION_CANDIDATES]:
        district = candidate.district or resolved_fallback_district
        raw_original_text = candidate.original_text or candidate.normalized_text
        if raw_original_text and (
            candidate.is_kocaeli_district
            or normalize_kocaeli_district(raw_original_text) is not None
        ):
            original_text = raw_original_text.strip()
        else:
            original_text = _clean_location_value(raw_original_text)
        neighborhood_text = _clean_location_value(candidate.neighborhood)
        if neighborhood_text and _is_malformed_neighborhood_text(neighborhood_text):
            neighborhood_text = None

        should_geocode_candidate = bool(
            candidate.district
            or neighborhood_text
            or candidate.is_kocaeli_district
            or looks_like_precise_location(original_text or "")
        )
        if original_text and is_generic_location_text(
            original_text,
            district_hint=candidate.district,
            neighborhood=neighborhood_text,
            is_kocaeli_district=candidate.is_kocaeli_district,
        ):
            should_geocode_candidate = False

        if neighborhood_text and district:
            add_input(
                address=f"{neighborhood_text}, {district}",
                district_hint=district,
                neighborhood=neighborhood_text,
            )
        elif neighborhood_text:
            add_input(
                address=neighborhood_text,
                district_hint=district,
                neighborhood=neighborhood_text,
            )

        if original_text and should_geocode_candidate:
            add_input(address=original_text, district_hint=district)
            if district and _normalize_for_compare(district) not in _normalize_for_compare(
                original_text
            ):
                add_input(
                    address=f"{original_text}, {district}",
                    district_hint=district,
                )

    if resolved_fallback_district:
        add_input(
            address=resolved_fallback_district,
            district_hint=resolved_fallback_district,
        )

    return list(deduped.values())


def looks_like_precise_location(value: str) -> bool:
    normalized = _normalize_for_compare(value)
    return any(hint in normalized for hint in _PRECISE_LOCATION_HINTS)


def _clean_location_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = normalize_location_text(value)
    if normalized:
        return normalized.strip()

    stripped = value.strip()
    return stripped or None


def _is_malformed_neighborhood_text(value: str) -> bool:
    normalized = _normalize_for_compare(value)
    if not normalized:
        return True

    parts = normalized.split()
    if not parts:
        return True

    return parts[0] in _INVALID_NEIGHBORHOOD_PREFIX_TOKENS


def is_generic_location_text(
    value: str,
    *,
    district_hint: str | None = None,
    neighborhood: str | None = None,
    is_kocaeli_district: bool = False,
) -> bool:
    normalized = _normalize_for_compare(value)
    if not normalized:
        return True
    if is_kocaeli_district or normalize_kocaeli_district(value):
        return False
    if neighborhood:
        return False
    if looks_like_precise_location(normalized):
        return False
    if normalized in _GENERIC_LOCATION_TOKENS:
        return True
    if normalized.endswith("spor") or normalized in _GENERIC_TEAM_ALIASES:
        return True
    if any(
        normalized.endswith(suffix) or f" {suffix}" in normalized
        for suffix in _GENERIC_LOCATION_HARD_SUFFIXES
    ):
        return True
    if any(
        normalized.endswith(suffix) or f" {suffix}" in normalized
        for suffix in _GENERIC_LOCATION_SOFT_SUFFIXES
    ):
        if _text_contains_kocaeli_district(normalized):
            return False
        if district_hint and _normalize_for_compare(district_hint) in normalized:
            return False
        return True
    return False


def _text_contains_kocaeli_district(normalized: str) -> bool:
    for district in KOCAELI_DISTRICTS:
        if re.search(rf"(?<!\w){re.escape(district)}(?!\w)", normalized):
            return True
    return False


def is_district_level_geocoding_input(input_data: GeocodingInput) -> bool:
    normalized_address = _normalize_for_compare(input_data.address)
    if normalize_kocaeli_district(input_data.address):
        return True

    if input_data.district_hint:
        normalized_hint = _normalize_for_compare(input_data.district_hint)
        if normalized_address == normalized_hint:
            return True

    return False
