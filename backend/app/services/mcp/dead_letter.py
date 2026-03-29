from __future__ import annotations
import json
import logging
import threading
from dataclasses import asdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .schemas import NewsWriteRequest

logger = logging.getLogger(__name__)

_DEAD_LETTER_KEY = "pulse:mcp:dead_letter"

try:
    import redis as redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


@dataclass
class DeadLetterItem:
    request: NewsWriteRequest
    failed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    final_error: str = ""
    attempt_count: int = 0


class DeadLetterStore:

    _MAX_SIZE = 200

    def __init__(self, redis_url: str | None = None) -> None:
        self._items: list[DeadLetterItem] = []
        self._lock = threading.Lock()
        self._redis = None

        if redis_url and _REDIS_AVAILABLE:
            try:
                self._redis = redis_lib.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=1,
                )
                self._redis.ping()
            except Exception as exc:
                logger.warning(
                    "mcp.dead_letter.redis_unavailable",
                    extra={"error": type(exc).__name__},
                )
                self._redis = None

    def add(
        self,
        request: NewsWriteRequest,
        error: str,
        attempt_count: int,
    ) -> None:
        if self._redis:
            item = DeadLetterItem(
                request=request,
                final_error=error,
                attempt_count=attempt_count,
            )
            try:
                self._redis.rpush(
                    _DEAD_LETTER_KEY,
                    json.dumps(asdict(item), ensure_ascii=False),
                )
                self._redis.ltrim(_DEAD_LETTER_KEY, -self._MAX_SIZE, -1)
            except Exception as exc:
                logger.warning(
                    "mcp.dead_letter.redis_add_failed",
                    extra={"error": type(exc).__name__},
                )

        with self._lock:
            if len(self._items) >= self._MAX_SIZE:
                # En eski item'ı çıkar — circular buffer
                self._items.pop(0)

            item = DeadLetterItem(
                request=request,
                final_error=error,
                attempt_count=attempt_count,
            )
            self._items.append(item)

        logger.error(
            "mcp.dead_letter.added",
            extra={
                "attempt_count": attempt_count,
                "error": error[:100],
                "dead_letter_size": self.size,
                **request.safe_log_repr(),
            },
        )

    def get_all(self) -> list[DeadLetterItem]:
        if self._redis:
            try:
                payloads = self._redis.lrange(_DEAD_LETTER_KEY, 0, -1)
                items: list[DeadLetterItem] = []
                for payload in payloads:
                    data = json.loads(payload)
                    items.append(
                        DeadLetterItem(
                            request=NewsWriteRequest(**data["request"]),
                            failed_at=data.get("failed_at", datetime.now(timezone.utc).isoformat()),
                            final_error=data.get("final_error", ""),
                            attempt_count=int(data.get("attempt_count", 0)),
                        )
                    )
                if items:
                    return items
            except Exception:
                pass

        with self._lock:
            return list(self._items)

    @property
    def size(self) -> int:
        if self._redis:
            try:
                return int(self._redis.llen(_DEAD_LETTER_KEY))
            except Exception:
                return 0
        with self._lock:
            return len(self._items)