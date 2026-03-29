from __future__ import annotations
import logging
from typing import Optional

import requests

from ..config import GeocodingConfig
from ..exceptions import ProviderError, ProviderRateLimitError
from ..schemas import GeocodingInput, GeocodingResult

logger = logging.getLogger(__name__)
_PROVIDER_VERSION = "opencage@1.0"


class OpenCageProvider:
    name = "opencage"

    def __init__(self, config: GeocodingConfig) -> None:
        self._cfg = config

    def geocode(self, input_data: GeocodingInput) -> Optional[GeocodingResult]:
        if not self._cfg.opencage_api_key:
            raise ProviderError("OpenCage API key tanımlanmamış")

        query = input_data.query_string()
        try:
            resp = requests.get(
                "https://api.opencagedata.com/geocode/v1/json",
                params={
                    "q": query,
                    "key": self._cfg.opencage_api_key,
                    "limit": 1,
                    "countrycode": "tr",
                    "language": "tr",
                    "no_annotations": 1,
                },
                timeout=self._cfg.timeout,
            )
        except requests.RequestException as exc:
            raise ProviderError(f"OpenCage HTTP hatası: {type(exc).__name__}")

        if resp.status_code == 402:
            raise ProviderRateLimitError(self.name, retry_after=3600.0)

        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])

        if not results:
            return None

        hit = results[0]
        geo = hit["geometry"]
        confidence = hit.get("confidence", 5) / 10.0  # OpenCage 1-10 → 0.1-1.0

        return GeocodingResult(
            address=input_data.address,
            lat=float(geo["lat"]),
            lng=float(geo["lng"]),
            display_name=hit.get("formatted", ""),
            confidence=round(confidence, 3),
            source="opencage",
            provider_version=_PROVIDER_VERSION,
            district=self._extract_district(hit),
        )

    def _extract_district(self, hit: dict) -> Optional[str]:
        components = hit.get("components", {})
        return (
            components.get("city_district")
            or components.get("town")
            or components.get("city")
            or components.get("county")
        )