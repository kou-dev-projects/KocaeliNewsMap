from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .schemas import NewsWriteRequest

logger = logging.getLogger(__name__)

_QUEUE_KEY = "pulse:mcp:write_queue"

try:
    import redis as redis_lib

    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


@dataclass
class QueueItem:
    request: NewsWriteRequest
    enqueued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attempt_count: int = 0
    last_error: str | None = None


class WriteQueue:
    def __init__(
        self,
        max_size: int,
        max_retries: int,
        redis_url: str | None = None,
        *,
        allow_memory_fallback: bool | None = None,
    ) -> None:
        self._queue: list[QueueItem] = []
        self._lock = threading.Lock()
        self._max_size = max_size
        self._max_retries = max_retries
        self._redis_url = redis_url
        self._redis: "redis_lib.Redis" | None = None
        self._allow_memory_fallback = (
            allow_memory_fallback if allow_memory_fallback is not None else redis_url is None
        )
        self._connect()

    def _connect(self) -> "redis_lib.Redis" | None:
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
                "mcp.queue.redis_unavailable",
                extra={"error": type(exc).__name__},
            )
            self._redis = None
        return self._redis

    def _get_redis(self) -> "redis_lib.Redis" | None:
        if self._redis is None:
            return self._connect()
        return self._redis

    def _handle_redis_error(self, exc: Exception, event: str) -> None:
        logger.warning(event, extra={"error": type(exc).__name__})
        self._redis = None

    def enqueue(self, request: NewsWriteRequest) -> bool:
        redis_client = self._get_redis()
        if redis_client is not None:
            try:
                if redis_client.llen(_QUEUE_KEY) >= self._max_size:
                    return False
                item = QueueItem(request=request)
                redis_client.rpush(_QUEUE_KEY, self._serialize_item(item))
                return True
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.queue.redis_enqueue_failed")
                if not self._allow_memory_fallback:
                    return False

        if not self._allow_memory_fallback:
            logger.error(
                "mcp.queue.memory_fallback_disabled",
                extra={"requested": request.safe_log_repr()},
            )
            return False

        with self._lock:
            if len(self._queue) >= self._max_size:
                logger.error(
                    "mcp.queue.full",
                    extra={
                        "max_size": self._max_size,
                        "dropped": request.safe_log_repr(),
                    },
                )
                return False

            self._queue.append(QueueItem(request=request))
            logger.info(
                "mcp.queue.enqueued",
                extra={
                    "queue_size": len(self._queue),
                    **request.safe_log_repr(),
                },
            )
            return True

    def dequeue_batch(self, size: int = 10) -> list[QueueItem]:
        redis_client = self._get_redis()
        if redis_client is not None:
            try:
                payloads = redis_client.lpop(_QUEUE_KEY, count=size)
                if payloads is None:
                    return []
                if isinstance(payloads, str):
                    payloads = [payloads]
                return [
                    item
                    for payload in payloads
                    if (item := self._deserialize_item(payload)) is not None
                ]
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.queue.redis_dequeue_failed")
                if not self._allow_memory_fallback:
                    return []

        if not self._allow_memory_fallback:
            return []

        with self._lock:
            batch = self._queue[:size]
            self._queue = self._queue[size:]
            return batch

    def requeue(self, item: QueueItem, error: str) -> bool:
        if item.attempt_count >= self._max_retries:
            logger.warning(
                "mcp.queue.max_retries_exceeded",
                extra={
                    "attempts": item.attempt_count,
                    "error": error[:100],
                    **item.request.safe_log_repr(),
                },
            )
            return False

        item.attempt_count += 1
        item.last_error = error

        redis_client = self._get_redis()
        if redis_client is not None:
            try:
                redis_client.rpush(_QUEUE_KEY, self._serialize_item(item))
                return True
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.queue.redis_requeue_failed")
                if not self._allow_memory_fallback:
                    return False

        if not self._allow_memory_fallback:
            return False

        with self._lock:
            self._queue.append(item)
            return True

    @property
    def size(self) -> int:
        redis_client = self._get_redis()
        if redis_client is not None:
            try:
                return int(redis_client.llen(_QUEUE_KEY))
            except Exception as exc:
                self._handle_redis_error(exc, "mcp.queue.redis_size_failed")
                if not self._allow_memory_fallback:
                    return 0
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        return self.size == 0

    @staticmethod
    def _serialize_item(item: QueueItem) -> str:
        return json.dumps(asdict(item), ensure_ascii=False)

    @staticmethod
    def _deserialize_item(payload: str) -> QueueItem | None:
        try:
            data = json.loads(payload)
            request = NewsWriteRequest(**data["request"])
            return QueueItem(
                request=request,
                enqueued_at=data.get("enqueued_at", datetime.now(timezone.utc).isoformat()),
                attempt_count=int(data.get("attempt_count", 0)),
                last_error=data.get("last_error"),
            )
        except Exception:
            return None
