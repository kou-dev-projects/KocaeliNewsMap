from __future__ import annotations

import re


_LEADING_UI_ARTIFACT_PATTERNS = (
    re.compile(
        r"^\s*(?:\+\d+\s+)?video\s+(?:için|icin)\s+play['’]e\s+(?:tıklayın|tiklayin)\s*(?:[-+|]\s*)*",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:\+\d+\s+)?haber\s+alb(?:ü|u)m(?:ü|u)\s+(?:için|icin)\s+resme\s+(?:tıklayın|tiklayin)\s*(?:[-+|]\s*)*",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:büyütmek|buyutmek)\s+(?:için|icin)\s+resme\s+(?:tıklayın|tiklayin)\s*(?:[-+|]\s*)*",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:whatsapp|twitle|paylaş|paylas|abone ol|google news)\s*(?:[-+|/]\s*)*",
        flags=re.IGNORECASE,
    ),
)

_INLINE_UI_ARTIFACT_PATTERNS = (
    re.compile(
        r"\b(?:büyütmek|buyutmek)\s+(?:için|icin)\s+resme\s+(?:tıklayın|tiklayin)\b\s*(?:[-+|]\s*)*",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bhaber\s+alb(?:ü|u)m(?:ü|u)\s+(?:için|icin)\s+resme\s+(?:tıklayın|tiklayin)\b\s*(?:[-+|]\s*)*",
        flags=re.IGNORECASE,
    ),
)

_WHITESPACE_RE = re.compile(r"\s+")


def repair_mojibake(value: str) -> str:
    try:
        return value.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def clean_news_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = repair_mojibake(str(value)).strip()
    if not cleaned:
        return None

    previous = None
    while cleaned != previous:
        previous = cleaned
        for pattern in _LEADING_UI_ARTIFACT_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        cleaned = cleaned.lstrip("-+|/ ").strip()

    for pattern in _INLINE_UI_ARTIFACT_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip(" -+|/")
    return cleaned or None
