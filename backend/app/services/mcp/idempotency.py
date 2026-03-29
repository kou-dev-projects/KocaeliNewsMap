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
        self._redis_url = redis_url
        self._ttl = ttl_seconds
        self._client: Optional["redis_lib.Redis"] = None
        self._connect()

    def _connect(self) -> Optional["redis_lib.Redis"]:
        if not _REDIS_AVAILABLE:
            logger.warning("mcp.idempotency.unavailable")
            self._client = None
            return None

        try:
            self._client = redis_lib.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=1,
            )
            self._client.ping()
        except Exception as exc:
            logger.warning(
                "mcp.idempotency.redis_unavailable",
                extra={"reason": type(exc).__name__},
            )
            self._client = None
        return self._client

    def _get_client(self) -> Optional["redis_lib.Redis"]:
        if self._client is None:
            return self._connect()
        return self._client

    def _handle_error(self, exc: Exception, event: str) -> None:
        logger.warning(event, extra={"error": type(exc).__name__})
        self._client = None

    def is_duplicate(self, idempotency_key: str) -> bool:
        client = self._get_client()
        if client is None:
            return False

        try:
            return bool(client.exists(self._key(idempotency_key)))
        except Exception as exc:
            self._handle_error(exc, "mcp.idempotency.exists_failed")
            return False

    def mark_processed(self, idempotency_key: str, news_id: str) -> None:
        client = self._get_client()
        if client is None:
            return

        try:
            client.setex(
                self._key(idempotency_key),
                self._ttl,
                news_id,
            )
        except Exception as exc:
            self._handle_error(exc, "mcp.idempotency.write_failed")

    def get_existing_id(self, idempotency_key: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None

        try:
            return client.get(self._key(idempotency_key))
        except Exception as exc:
            self._handle_error(exc, "mcp.idempotency.get_failed")
            return None

    def _key(self, idempotency_key: str) -> str:
        return f"{_IDEMPOTENCY_KEY_PREFIX}:{idempotency_key}"
