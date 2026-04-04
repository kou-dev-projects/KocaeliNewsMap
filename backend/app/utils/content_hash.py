from __future__ import annotations

import hashlib
import re

from app.utils.content_cleaning import clean_news_text

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def compute_content_hash(title: str, body: str) -> str:
    safe_title = (title or "").strip()
    safe_body = (body or "").strip()
    payload = f"{safe_title}\n{safe_body}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compute_duplicate_hash(
    *,
    title: str,
    body: str,
    summary: str | None = None,
    token_limit: int = 80,
) -> str:
    seed = (
        clean_news_text(summary or "")
        or clean_news_text(body or "")
        or clean_news_text(title or "")
        or ""
    )
    tokens = _TOKEN_PATTERN.findall(seed.casefold())
    normalized = " ".join(tokens[:token_limit])
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
