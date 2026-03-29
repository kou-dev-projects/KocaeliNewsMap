from __future__ import annotations
import json
import logging
import threading
from dataclasses import asdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

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
    enqueued_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    attempt_count: int = 0
    last_error: Optional[str] = None


class WriteQueue:

    def __init__(
        self,
        max_size: int,
        max_retries: int,
        redis_url: str | None = None,
    ) -> None:
        self._queue: list[QueueItem] = []
        self._lock = threading.Lock()
        self._max_size = max_size
        self._max_retries = max_retries
        self._redis: Optional["redis_lib.Redis"] = None

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
                    "mcp.queue.redis_unavailable",
                    extra={"error": type(exc).__name__},
                )
                self._redis = None

    def enqueue(self, request: NewsWriteRequest) -> bool:
       
        if self._redis:
            try:
                if self._redis.llen(_QUEUE_KEY) >= self._max_size:
                    return False
                item = QueueItem(request=request)
                self._redis.rpush(_QUEUE_KEY, self._serialize_item(item))
                return True
            except Exception as exc:
                logger.warning(
                    "mcp.queue.redis_enqueue_failed",
                    extra={"error": type(exc).__name__},
                )

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
        if self._redis:
            items: list[QueueItem] = []
            try:
                payloads = self._redis.lpop(_QUEUE_KEY, count=size)
                if payloads is None:
                    return []
                if isinstance(payloads, str):
                    payloads = [payloads]
                for payload in payloads:
                    item = self._deserialize_item(payload)
                    if item:
                        items.append(item)
                return items
            except Exception as exc:
                logger.warning(
                    "mcp.queue.redis_dequeue_failed",
                    extra={"error": type(exc).__name__},
                )

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

        if self._redis:
            try:
                item.attempt_count += 1
                item.last_error = error
                self._redis.rpush(_QUEUE_KEY, self._serialize_item(item))
                return True
            except Exception as exc:
                logger.warning(
                    "mcp.queue.redis_requeue_failed",
                    extra={"error": type(exc).__name__},
                )

        with self._lock:
            item.attempt_count += 1
            item.last_error = error
            self._queue.append(item)
            return True

    @property
    def size(self) -> int:
        if self._redis:
            try:
                return int(self._redis.llen(_QUEUE_KEY))
            except Exception:
                return 0
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        return self.size == 0

    def _serialize_item(self, item: QueueItem) -> str:
        payload = asdict(item)
        return json.dumps(payload, ensure_ascii=False)

    def _deserialize_item(self, payload: str) -> QueueItem | None:
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