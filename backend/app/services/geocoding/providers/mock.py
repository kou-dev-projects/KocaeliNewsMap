from __future__ import annotations
from typing import Optional
from ..schemas import GeocodingInput, GeocodingResult

_PROVIDER_VERSION = "mock@1.0"

_KOCAELI_COORDS: dict[str, tuple[float, float]] = {
    "izmit":      (40.7654, 29.9408),
    "gebze":      (40.8021, 29.4313),
    "darıca":     (40.7611, 29.3722),
    "gölcük":     (40.6526, 29.8254),
    "körfez":     (40.7693, 29.7780),
    "kartepe":    (40.6931, 30.0736),
    "başiskele":  (40.7362, 29.8954),
    "çayırova":   (40.8021, 29.3722),
    "dilovası":   (40.7711, 29.5441),
    "kandıra":    (41.0742, 30.1572),
    "karamürsel": (40.6813, 29.6098),
    "derince":    (40.7456, 29.8234),
}


class MockGeocodingProvider:
    name = "mock"

    def geocode(self, input_data: GeocodingInput) -> Optional[GeocodingResult]:
        key = input_data.address.lower()

        for district, (lat, lng) in _KOCAELI_COORDS.items():
            if district in key:
                return self._result(input_data.address, district, lat, lng, 0.95)

        if input_data.district_hint:
            hint = input_data.district_hint.lower()
            for district, (lat, lng) in _KOCAELI_COORDS.items():
                if district in hint:
                    return self._result(input_data.address, district, lat, lng, 0.80)

        return None

    def _result(
        self, address: str, district: str, lat: float, lng: float, confidence: float
    ) -> GeocodingResult:
        return GeocodingResult(
            address=address,
            lat=lat,
            lng=lng,
            display_name=f"{district.title()}, Kocaeli, Türkiye",
            confidence=confidence,
            source="mock",
            provider_version=_PROVIDER_VERSION,
            district=district,
        )