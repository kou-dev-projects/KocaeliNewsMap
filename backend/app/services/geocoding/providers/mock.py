from __future__ import annotations
from typing import Optional
from ..schemas import GeocodingInput, GeocodingResult, _normalize_for_compare

_PROVIDER_VERSION = "mock@1.0"

_RAW_KOCAELI_COORDS: dict[str, tuple[float, float]] = {
    "İzmit": (40.7654, 29.9408),
    "Gebze": (40.8021, 29.4313),
    "Darıca": (40.7611, 29.3722),
    "Gölcük": (40.6526, 29.8254),
    "Körfez": (40.7693, 29.7780),
    "Kartepe": (40.6931, 30.0736),
    "Başiskele": (40.7362, 29.8954),
    "Çayırova": (40.8021, 29.3722),
    "Dilovası": (40.7711, 29.5441),
    "Kandıra": (41.0742, 30.1572),
    "Karamürsel": (40.6813, 29.6098),
    "Derince": (40.7456, 29.8234),
}

_KOCAELI_COORDS: dict[str, tuple[str, float, float]] = {
    _normalize_for_compare(name): (name, lat, lng)
    for name, (lat, lng) in _RAW_KOCAELI_COORDS.items()
}


class MockGeocodingProvider:
    name = "mock"

    def geocode(self, input_data: GeocodingInput) -> Optional[GeocodingResult]:
        key = _normalize_for_compare(input_data.address)

        for district, (display_name, lat, lng) in _KOCAELI_COORDS.items():
            if district in key:
                return self._result(
                    input_data.address,
                    district,
                    display_name,
                    lat,
                    lng,
                    0.95,
                )

        if input_data.district_hint:
            hint = _normalize_for_compare(input_data.district_hint)
            for district, (display_name, lat, lng) in _KOCAELI_COORDS.items():
                if district in hint:
                    return self._result(
                        input_data.address,
                        district,
                        display_name,
                        lat,
                        lng,
                        0.80,
                    )

        return None

    def _result(
        self,
        address: str,
        district: str,
        display_name: str,
        lat: float,
        lng: float,
        confidence: float,
    ) -> GeocodingResult:
        return GeocodingResult(
            address=address,
            lat=lat,
            lng=lng,
            display_name=f"{display_name}, Kocaeli, Türkiye",
            confidence=confidence,
            source="mock",
            provider_version=_PROVIDER_VERSION,
            district=district,
        )
