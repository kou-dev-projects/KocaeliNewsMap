from __future__ import annotations

import logging
from collections import OrderedDict

from app.domain.enums import normalize_kocaeli_district

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
_MAX_LOCATION_CANDIDATES = 5
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
    "terminali",
    "kavsagi",
    "meydani",
)


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
) -> GeocodingInput | None:
    inputs = build_geocoding_inputs_from_ner(ner_result, news_id=news_id)
    return inputs[0] if inputs else None


def build_geocoding_inputs_from_ner(
    ner_result: NERResult,
    news_id: str | None = None,
) -> list[GeocodingInput]:
    if not ner_result.location_candidates and not ner_result.validated_districts:
        return []

    deduped: OrderedDict[
        tuple[str, str | None, str | None],
        GeocodingInput,
    ] = OrderedDict()

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
        clean_neighborhood = neighborhood.strip() if neighborhood else None
        if not clean_address:
            return

        key = (
            _normalize_for_compare(clean_address),
            _normalize_for_compare(clean_district) if clean_district else None,
            _normalize_for_compare(clean_neighborhood)
            if clean_neighborhood
            else None,
        )
        if key in deduped:
            return

        deduped[key] = GeocodingInput(
            address=clean_address,
            district_hint=clean_district,
            neighborhood=clean_neighborhood,
            news_id=news_id,
        )

    fallback_district = next(
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

    for candidate in ner_result.location_candidates[:_MAX_LOCATION_CANDIDATES]:
        district = candidate.district or fallback_district
        original_text = (
            candidate.original_text.strip() if candidate.original_text else None
        )
        should_geocode_candidate = bool(
            district
            or candidate.neighborhood
            or candidate.is_kocaeli_district
            or _looks_like_precise_location(original_text or "")
        )
        if original_text and _is_generic_location_text(original_text):
            should_geocode_candidate = False

        if candidate.neighborhood and district:
            add_input(
                address=f"{candidate.neighborhood}, {district}",
                district_hint=district,
                neighborhood=candidate.neighborhood,
            )
        elif candidate.neighborhood:
            add_input(
                address=candidate.neighborhood,
                district_hint=district,
                neighborhood=candidate.neighborhood,
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

        if district and _looks_like_precise_location(original_text or ""):
            add_input(address=district, district_hint=district)

    if fallback_district:
        add_input(address=fallback_district, district_hint=fallback_district)

    return list(deduped.values())


def _looks_like_precise_location(value: str) -> bool:
    normalized = _normalize_for_compare(value)
    return any(hint in normalized for hint in _PRECISE_LOCATION_HINTS)


def _is_generic_location_text(value: str) -> bool:
    normalized = _normalize_for_compare(value)
    if not normalized:
        return True
    return normalized in _GENERIC_LOCATION_TOKENS


def is_district_level_geocoding_input(input_data: GeocodingInput) -> bool:
    normalized_address = _normalize_for_compare(input_data.address)
    if normalize_kocaeli_district(input_data.address):
        return True

    if input_data.district_hint:
        normalized_hint = _normalize_for_compare(input_data.district_hint)
        if normalized_address == normalized_hint:
            return True

    return False
