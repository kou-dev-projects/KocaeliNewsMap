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
        self._redis_url = redis_url
        self._redis = None
        self._connect()

    def _connect(self):
        if not self._redis_url or not _REDIS_AVAILABLE:
            self._redis = None
            return None

        try:
            self._redis = redis_lib.from_url(
                self._redis_url,
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
        return self._redis

    def _get_redis(self):
        if self._redis is None:
            return self._connect()
        return self._redis

    def _handle_redis_error(self, exc: Exception, event: str) -> None:
        logger.warning(event, extra={"error": type(exc).__name__})
        self._redis = None

    def add(
        self,
        request: NewsWriteRequest,
        error: str,
        attempt_count: int,
    ) -> None:
        item = DeadLetterItem(
            request=request,
            final_error=error,
            attempt_count=attempt_count,
        )
        redis_client = self._get_redis()
        if redis_client:
            try:
                redis_client.rpush(
                    _DEAD_LETTER_KEY,
                    json.dumps(asdict(item), ensure_ascii=False),
                )
                redis_client.ltrim(_DEAD_LETTER_KEY, -self._MAX_SIZE, -1)
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.dead_letter.redis_add_failed")

        with self._lock:
            if len(self._items) >= self._MAX_SIZE:
                self._items.pop(0)
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
        redis_client = self._get_redis()
        if redis_client:
            try:
                payloads = redis_client.lrange(_DEAD_LETTER_KEY, 0, -1)
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
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.dead_letter.redis_get_failed")

        with self._lock:
            return list(self._items)

    @property
    def size(self) -> int:
        redis_client = self._get_redis()
        if redis_client:
            try:
                return int(redis_client.llen(_DEAD_LETTER_KEY))
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.dead_letter.redis_size_failed")

        with self._lock:
            return len(self._items)
