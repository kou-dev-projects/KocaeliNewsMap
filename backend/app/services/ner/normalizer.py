from __future__ import annotations

import re

from .morphology import strip_suffixes


_TRAILING_PUNCTUATION = r'["“”()\[\],.;:!?]+$'
_LEADING_PUNCTUATION = r'^["“”(]+'


def normalize_location_text(text: str) -> str:
    value = text.strip()

    if not value:
        return ""

    value = value.replace("\u2019", "'")
    value = re.sub(_TRAILING_PUNCTUATION, "", value)
    value = re.sub(_LEADING_PUNCTUATION, "", value)
    value = strip_suffixes(value)

    return value.strip()
