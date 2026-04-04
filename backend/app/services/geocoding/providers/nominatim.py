from __future__ import annotations

import logging
import re
import time
from typing import Optional

import requests

from ..config import GeocodingConfig
from ..exceptions import ProviderError, ProviderRateLimitError, ProviderUnavailableError
from ..provider_versions import PROVIDER_VERSIONS
from ..schemas import GeocodingInput, GeocodingResult, _normalize_for_compare

logger = logging.getLogger(__name__)

_RATE_LIMIT_INTERVAL = 1.1
_PROVIDER_VERSION = PROVIDER_VERSIONS["nominatim"]
_MAX_RESULTS = 5
_PRECISE_QUERY_HINTS = (
    "mahallesi",
    "mahalle",
    "mah.",
    "sokak",
    "cadde",
    "caddesi",
    "bulvari",
    "bulvar",
    "baraji",
    "goleti",
    "tesisi",
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
_PRECISE_RESULT_TYPES = {
    "amenity",
    "building",
    "house",
    "locality",
    "neighbourhood",
    "neighborhood",
    "quarter",
    "reservoir",
    "street",
    "suburb",
    "village",
}
_ADMIN_RESULT_TYPES = {
    "administrative",
    "borough",
    "city",
    "county",
    "municipality",
    "province",
    "state",
    "town",
}
_KOCAELI_HINTS = {"kocaeli", "izmit"}


class NominatimProvider:
    name = "nominatim"

    def __init__(self, config: GeocodingConfig) -> None:
        self._cfg = config
        self._last_request_at = 0.0

    def geocode(self, input_data: GeocodingInput) -> Optional[GeocodingResult]:
        query = input_data.query_string()
        self._rate_limit()

        last_exc: Optional[Exception] = None
        for attempt in range(self._cfg.max_retries + 1):
            try:
                return self._request(query, input_data)
            except ProviderRateLimitError:
                raise
            except ProviderError as exc:
                last_exc = exc
                if attempt < self._cfg.max_retries:
                    wait = 1.5**attempt
                    logger.info(
                        "geocoding.provider.retry",
                        extra={
                            "provider": self.name,
                            "attempt": attempt + 1,
                            "wait_seconds": round(wait, 2),
                            "error": str(exc)[:80],
                        },
                    )
                    time.sleep(wait)

        raise ProviderUnavailableError(
            f"Nominatim {self._cfg.max_retries} denemede basarisiz: {last_exc}"
        )

    def _request(
        self,
        query: str,
        input_data: GeocodingInput,
    ) -> Optional[GeocodingResult]:
        try:
            resp = requests.get(
                f"{self._cfg.nominatim_url}/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": _MAX_RESULTS,
                    "addressdetails": 1,
                    "namedetails": 1,
                    "countrycodes": "tr",
                    "accept-language": "tr",
                },
                headers={"User-Agent": self._cfg.user_agent},
                timeout=self._cfg.timeout,
            )
        except requests.Timeout:
            raise ProviderError(f"Nominatim timeout ({self._cfg.timeout}s)")
        except requests.ConnectionError:
            raise ProviderUnavailableError("Nominatim baglanti kurulamadi")
        except requests.RequestException as exc:
            raise ProviderError(f"Nominatim HTTP hatasi: {type(exc).__name__}")

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 1.0))
            raise ProviderRateLimitError(self.name, retry_after)

        if resp.status_code >= 500:
            raise ProviderUnavailableError(f"Nominatim 5xx: {resp.status_code}")

        try:
            resp.raise_for_status()
            results = resp.json()
        except Exception as exc:
            raise ProviderError(f"Nominatim yanit parse hatasi: {type(exc).__name__}")

        if not results:
            return None

        hit, confidence = self._select_best_hit(results, input_data)
        return GeocodingResult(
            address=input_data.address,
            lat=float(hit["lat"]),
            lng=float(hit["lon"]),
            display_name=hit.get("display_name", ""),
            confidence=confidence,
            source="nominatim",
            provider_version=_PROVIDER_VERSION,
            district=self._extract_district(hit),
        )

    def _select_best_hit(
        self,
        results: list[dict],
        input_data: GeocodingInput,
    ) -> tuple[dict, float]:
        scored_hits = [(hit, self._confidence(hit, input_data)) for hit in results]
        best_hit, best_score = max(scored_hits, key=lambda item: item[1])
        logger.info(
            "geocoding.nominatim.selected_hit",
            extra={
                "address": input_data.address[:80],
                "query": input_data.query_string()[:120],
                "top_score": best_score,
                "candidate_count": len(results),
                "display_name": str(best_hit.get("display_name", ""))[:120],
            },
        )
        return best_hit, best_score

    def _confidence(self, hit: dict, input_data: GeocodingInput) -> float:
        search_blob = self._build_search_blob(hit)
        normalized_address = _normalize_for_compare(input_data.address)
        tokens = self._meaningful_tokens(input_data.address)
        district_hint = (
            _normalize_for_compare(input_data.district_hint)
            if input_data.district_hint
            else None
        )
        extracted_district = _normalize_for_compare(self._extract_district(hit) or "")
        result_type = _normalize_for_compare(str(hit.get("type", "")))
        address_type = _normalize_for_compare(str(hit.get("addresstype", "")))

        score = 0.0

        if normalized_address and normalized_address in search_blob:
            score += 0.42

        if tokens:
            matched_tokens = sum(1 for token in tokens if token in search_blob)
            score += 0.33 * (matched_tokens / len(tokens))

        if district_hint:
            if extracted_district == district_hint or district_hint in search_blob:
                score += 0.22
            else:
                score -= 0.14

        if any(hint in search_blob for hint in _KOCAELI_HINTS):
            score += 0.15
        else:
            score -= 0.08

        if self._looks_like_precise_query(input_data):
            if (
                result_type in _PRECISE_RESULT_TYPES
                or address_type in _PRECISE_RESULT_TYPES
            ):
                score += 0.14
            if (
                result_type in _ADMIN_RESULT_TYPES
                or address_type in _ADMIN_RESULT_TYPES
            ):
                score -= 0.30
        elif (
            result_type in _ADMIN_RESULT_TYPES
            or address_type in _ADMIN_RESULT_TYPES
        ):
            score += 0.08

        try:
            importance = max(0.0, min(float(hit.get("importance", 0.0)), 1.0))
        except (TypeError, ValueError):
            importance = 0.0
        score += 0.08 * importance

        return round(max(0.0, min(score, 1.0)), 3)

    def _build_search_blob(self, hit: dict) -> str:
        parts = [hit.get("display_name", "")]
        address = hit.get("address", {})
        namedetails = hit.get("namedetails", {})

        if isinstance(address, dict):
            parts.extend(str(value) for value in address.values() if value)
        if isinstance(namedetails, dict):
            parts.extend(str(value) for value in namedetails.values() if value)

        return _normalize_for_compare(" ".join(parts))

    def _looks_like_precise_query(self, input_data: GeocodingInput) -> bool:
        normalized = _normalize_for_compare(
            " ".join(part for part in (input_data.neighborhood, input_data.address) if part)
        )
        return any(hint in normalized for hint in _PRECISE_QUERY_HINTS)

    def _meaningful_tokens(self, value: str) -> list[str]:
        normalized = _normalize_for_compare(value)
        return [
            token
            for token in re.findall(r"[a-z0-9]+", normalized)
            if len(token) > 2 and token not in {"kocaeli", "turkiye", "turkey"}
        ]

    def _extract_district(self, hit: dict) -> Optional[str]:
        addr = hit.get("address", {})
        return (
            addr.get("city_district")
            or addr.get("town")
            or addr.get("municipality")
            or addr.get("suburb")
            or addr.get("city")
            or addr.get("county")
        )

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _RATE_LIMIT_INTERVAL:
            time.sleep(_RATE_LIMIT_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()
