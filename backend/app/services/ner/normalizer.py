from __future__ import annotations

import re


_SUFFIX_PATTERNS = (
    r"(?:'|’)(de|da|te|ta)$",
    r"(?:'|’)(den|dan|ten|tan)$",
    r"(?:'|’)(ye|ya)$",
    r"(?:'|’)(yi|yı|yu|yü)$",
    r"(?:'|’)(nin|nın|nun|nün)$",
    r"(?:'|’)(in|ın|un|ün)$",
    r"(?:'|’)(e|a)$",
    r"(?:'|’)(i|ı|u|ü)$",
)


def normalize_location_text(text: str) -> str:
    value = text.strip()

    if not value:
        return ""

    for pattern in _SUFFIX_PATTERNS:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

    value = re.sub(r"[\"“”()\[\],.;:!?]+$", "", value)
    value = re.sub(r"^[\"“”(]+", "", value)

    return value.strip()
