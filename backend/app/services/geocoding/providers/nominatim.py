from __future__ import annotations
import logging
import time
from typing import Optional

import requests

from ..config import GeocodingConfig
from ..exceptions import ProviderError, ProviderRateLimitError, ProviderUnavailableError
from ..schemas import GeocodingInput, GeocodingResult

logger = logging.getLogger(__name__)

_RATE_LIMIT_INTERVAL = 1.1   # Nominatim public policy
_PROVIDER_VERSION = "nominatim@1.0"


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
                return self._request(query, input_data.address)
            except ProviderRateLimitError:
                raise   # Rate limit → caller queue'ya alır, retry etmez
            except ProviderError as exc:
                last_exc = exc
                if attempt < self._cfg.max_retries:
                    wait = 1.5 ** attempt   # exponential backoff: 1s, 1.5s, 2.25s
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
            f"Nominatim {self._cfg.max_retries} denemede başarısız: {last_exc}"
        )

    def _request(self, query: str, original_address: str) -> Optional[GeocodingResult]:
        try:
            resp = requests.get(
                f"{self._cfg.nominatim_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                    "countrycodes": "tr",
                    "accept-language": "tr",
                },
                headers={"User-Agent": self._cfg.user_agent},
                timeout=self._cfg.timeout,
            )
        except requests.Timeout:
            raise ProviderError(f"Nominatim timeout ({self._cfg.timeout}s)")
        except requests.ConnectionError:
            raise ProviderUnavailableError("Nominatim bağlantı kurulamadı")
        except requests.RequestException as exc:
            raise ProviderError(f"Nominatim HTTP hatası: {type(exc).__name__}")

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 1.0))
            raise ProviderRateLimitError(self.name, retry_after)

        if resp.status_code >= 500:
            raise ProviderUnavailableError(f"Nominatim 5xx: {resp.status_code}")

        try:
            resp.raise_for_status()
            results = resp.json()
        except Exception as exc:
            raise ProviderError(f"Nominatim yanıt parse hatası: {type(exc).__name__}")

        if not results:
            return None

        hit = results[0]
        return GeocodingResult(
            address=original_address,
            lat=float(hit["lat"]),
            lng=float(hit["lon"]),
            display_name=hit.get("display_name", ""),
            confidence=self._confidence(hit),
            source="nominatim",
            provider_version=_PROVIDER_VERSION,
            district=self._extract_district(hit),
        )

    def _confidence(self, hit: dict) -> float:
        importance = float(hit.get("importance", 0.5))
        display = hit.get("display_name", "").lower()
        if "kocaeli" not in display and "izmit" not in display:
            importance *= 0.4   # Kocaeli dışı sonuçlara güçlü ceza
        return round(min(importance, 1.0), 3)

    def _extract_district(self, hit: dict) -> Optional[str]:
        addr = hit.get("address", {})
        return (
            addr.get("city_district")
            or addr.get("town")
            or addr.get("city")
            or addr.get("county")
        )

    def _rate_limit(self) -> None:
       
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _RATE_LIMIT_INTERVAL:
            time.sleep(_RATE_LIMIT_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()