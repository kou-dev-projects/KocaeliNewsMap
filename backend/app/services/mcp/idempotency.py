from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_IDEMPOTENCY_KEY_PREFIX = "pulse:idem:v1"

try:
    import redis as redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


class IdempotencyStore:

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._client: Optional["redis_lib.Redis"] = None

        if not _REDIS_AVAILABLE:
            logger.warning("mcp.idempotency.unavailable")
            return

        try:
            self._client = redis_lib.from_url(
                redis_url, decode_responses=True,
                socket_connect_timeout=2, socket_timeout=1,
            )
            self._client.ping()
        except Exception as exc:
            logger.warning(
                "mcp.idempotency.redis_unavailable",
                extra={"reason": type(exc).__name__},
            )
            self._client = None

    def is_duplicate(self, idempotency_key: str) -> bool:

        if not self._client:
            # Redis yoksa duplicate check yapılamaz
            # MongoDB unique index devreye girer
            return False

        key = self._key(idempotency_key)
        return bool(self._client.exists(key))

    def mark_processed(self, idempotency_key: str, news_id: str) -> None:
       
        if not self._client:
            return

        self._client.setex(
            self._key(idempotency_key),
            self._ttl,
            news_id,
        )

    def get_existing_id(self, idempotency_key: str) -> Optional[str]:
       
        if not self._client:
            return None
        return self._client.get(self._key(idempotency_key))

    def _key(self, idempotency_key: str) -> str:
        return f"{_IDEMPOTENCY_KEY_PREFIX}:{idempotency_key}"