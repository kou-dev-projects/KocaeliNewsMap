from __future__ import annotations

import unicodedata

KOCAELI_DISTRICTS = {
    "izmit": "İzmit",
    "gebze": "Gebze",
    "darica": "Darıca",
    "golcuk": "Gölcük",
    "korfez": "Körfez",
    "kartepe": "Kartepe",
    "basiskele": "Başiskele",
    "cayirova": "Çayırova",
    "dilovasi": "Dilovası",
    "kandira": "Kandıra",
    "karamursel": "Karamürsel",
    "derince": "Derince",
}


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
