from __future__ import annotations

from typing import Optional

from app.domain.enums import normalize_kocaeli_district

_DISTRICT_CENTERS: dict[str, tuple[float, float]] = {
    "izmit": (40.7654, 29.9408),
    "gebze": (40.8021, 29.4313),
    "darica": (40.7611, 29.3722),
    "golcuk": (40.6526, 29.8254),
    "hereke": (40.7855, 29.6153),
    "korfez": (40.7693, 29.7780),
    "kartepe": (40.6931, 30.0736),
    "basiskele": (40.7362, 29.8954),
    "cayirova": (40.8021, 29.3722),
    "dilovasi": (40.7711, 29.5441),
    "kandira": (41.0742, 30.1572),
    "karamursel": (40.6813, 29.6098),
    "derince": (40.7456, 29.8234),
}


def get_kocaeli_district_center(
    district: str | None,
) -> Optional[tuple[str, float, float]]:
    district_enum = normalize_kocaeli_district(district)
    if district_enum is None:
        return None

    center = _DISTRICT_CENTERS.get(district_enum.value)
    if center is None:
        return None

    lat, lng = center
    return district_enum.value, lat, lng
