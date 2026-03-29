from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


WHITESPACE_RE = re.compile(r"\s+")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def html_to_text(html: str | None) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return clean_text(soup.get_text(" ", strip=True))


def to_absolute_url(base_url: str, maybe_relative_url: str | None) -> str:
    if not maybe_relative_url:
        return ""
    return urljoin(base_url, maybe_relative_url.strip())


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    url = url.strip()
    parsed = urlparse(url)
    normalized = parsed._replace(fragment="")
    return normalized.geturl().rstrip("/")


def unique_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for url in urls:
        normalized = normalize_url(url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)

    return result