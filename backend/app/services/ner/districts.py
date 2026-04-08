from __future__ import annotations

import re
import unicodedata

KOCAELI_DISTRICTS = {
    "izmit": "İzmit",
    "gebze": "Gebze",
    "darica": "Darıca",
    "golcuk": "Gölcük",
    "hereke": "Hereke",
    "korfez": "Körfez",
    "kartepe": "Kartepe",
    "basiskele": "Başiskele",
    "cayirova": "Çayırova",
    "dilovasi": "Dilovası",
    "kandira": "Kandıra",
    "karamursel": "Karamürsel",
    "derince": "Derince",
}

_DISTRICT_SUFFIXES = frozenset(
    {
        "de",
        "da",
        "te",
        "ta",
        "den",
        "dan",
        "ten",
        "tan",
        "deki",
        "daki",
        "teki",
        "taki",
        "il",
        "ilce",
        "ilcesi",
        "ilcesinde",
    }
)

_DISTRICT_EXTENDED_SPAN_PREFIXES = tuple(
    sorted(
        {
            "tem",
            "d100",
            "d 100",
            "d-100",
            "otoyolu",
            "otoyolunda",
            "sanayi",
            "sanayi sitesi",
            "sahil",
            "sahilinde",
            "liman",
            "limani",
        },
        key=len,
        reverse=True,
    )
)


def normalize_for_compare(text: str) -> str:
    value = text.strip()

    value = value.replace("İ", "I")
    value = value.replace("ı", "i")

    value = value.lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))

    replacements = {
        "ç": "c",
        "ğ": "g",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
        "'": "",
        "’": "",
        "-": " ",
    }

    for src, target in replacements.items():
        value = value.replace(src, target)

    return " ".join(value.split())


def is_kocaeli_district(text: str) -> bool:
    normalized = normalize_for_compare(text)
    return normalized in KOCAELI_DISTRICTS


def canonical_district_name(text: str) -> str | None:
    normalized = normalize_for_compare(text)
    return KOCAELI_DISTRICTS.get(normalized)


def _matches_name_with_suffix(
    normalized: str,
    key: str,
    allowed_suffixes: frozenset[str],
) -> bool:
    if normalized == key:
        return True

    if not normalized.startswith(key):
        return False

    suffix = normalized[len(key):]
    return suffix in allowed_suffixes


def recover_district_name(text: str) -> str | None:
    normalized = normalize_for_compare(text)

    exact = KOCAELI_DISTRICTS.get(normalized)
    if exact:
        return exact

    for key, canonical in KOCAELI_DISTRICTS.items():
        if _matches_name_with_suffix(normalized, key, _DISTRICT_SUFFIXES):
            return canonical
        if _matches_extended_district_span(normalized, key):
            return canonical

    return None


def _matches_extended_district_span(normalized: str, key: str) -> bool:
    prefix = f"{key} "
    if not normalized.startswith(prefix):
        return False

    remainder = normalized[len(prefix):].strip()
    if not remainder:
        return False

    if any(
        remainder.startswith(candidate)
        for candidate in _DISTRICT_EXTENDED_SPAN_PREFIXES
    ):
        return True

    return re.match(r"^[a-z]*\d", remainder) is not None
