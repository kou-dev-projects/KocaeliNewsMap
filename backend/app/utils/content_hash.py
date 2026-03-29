from __future__ import annotations

import hashlib


def compute_content_hash(title: str, body: str) -> str:
    safe_title = (title or "").strip()
    safe_body = (body or "").strip()
    payload = f"{safe_title}\n{safe_body}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
