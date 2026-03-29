from enum import Enum
from typing import Optional


def _ascii_fold(value: str) -> str:
    mapping = str.maketrans(
        {
            "ç": "c",
            "Ç": "c",
            "ğ": "g",
            "Ğ": "g",
            "ı": "i",
            "İ": "i",
            "ö": "o",
            "Ö": "o",
            "ş": "s",
            "Ş": "s",
            "ü": "u",
            "Ü": "u",
        }
    )
    return value.translate(mapping)


def _normalize_token(value: str) -> str:
    normalized = _ascii_fold(value).strip().lower()
    normalized = normalized.replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


class NewsCategory(str, Enum):
    TRAFIK_KAZASI = "trafik_kazasi"
    YANGIN = "yangin"
    HIRSIZLIK = "hirsizlik"
    ELEKTRIK_KESINTISI = "elektrik_kesintisi"
    KULTUREL_ETKINLIK = "kulturel_etkinlik"
    UNKNOWN = "unknown"


class KocaeliDistrict(str, Enum):
    IZMIT = "izmit"
    GEBZE = "gebze"
    DARICA = "darica"
    GOLCUK = "golcuk"
    HEREKE = "hereke"
    KORFEZ = "korfez"
    KARTEPE = "kartepe"
    BASISKELE = "basiskele"
    CAYIROVA = "cayirova"
    DILOVASI = "dilovasi"
    KANDIRA = "kandira"
    KARAMURSEL = "karamursel"
    DERINCE = "derince"


_CATEGORY_ALIASES = {
    "trafik_kazasi": NewsCategory.TRAFIK_KAZASI,
    "trafik_kazasi_haberi": NewsCategory.TRAFIK_KAZASI,
    "trafik_kazasi_haber": NewsCategory.TRAFIK_KAZASI,
    "trafik_kazasi_olayi": NewsCategory.TRAFIK_KAZASI,
    "yangin": NewsCategory.YANGIN,
    "hirsizlik": NewsCategory.HIRSIZLIK,
    "elektrik_kesintisi": NewsCategory.ELEKTRIK_KESINTISI,
    "kulturel_etkinlik": NewsCategory.KULTUREL_ETKINLIK,
    "kulturel_etkinlikler": NewsCategory.KULTUREL_ETKINLIK,
    "unknown": NewsCategory.UNKNOWN,
}

_DISTRICT_ALIASES = {
    district.value: district
    for district in KocaeliDistrict
}


def normalize_news_category(value: Optional[str | NewsCategory]) -> Optional[NewsCategory]:
    if value is None:
        return None
    if isinstance(value, NewsCategory):
        return value

    normalized = _normalize_token(value)
    return _CATEGORY_ALIASES.get(normalized)


def normalize_kocaeli_district(value: Optional[str | KocaeliDistrict]) -> Optional[KocaeliDistrict]:
    if value is None:
        return None
    if isinstance(value, KocaeliDistrict):
        return value

    normalized = _normalize_token(value)
    return _DISTRICT_ALIASES.get(normalized)
