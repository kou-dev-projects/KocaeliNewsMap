from __future__ import annotations

import threading
from collections import defaultdict


_fallback_hits: dict[str, int] = defaultdict(int)
_lock = threading.Lock()


def record_fallback_hit(*, source: str, stage: str, fallback: str) -> int:
    key = f"{source}|{stage}|{fallback}"
    with _lock:
        _fallback_hits[key] += 1
        return _fallback_hits[key]


def snapshot_fallback_hits() -> dict[str, int]:
    with _lock:
        return dict(_fallback_hits)
