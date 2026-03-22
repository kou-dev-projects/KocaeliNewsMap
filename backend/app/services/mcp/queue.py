from __future__ import annotations
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .schemas import NewsWriteRequest

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    request: NewsWriteRequest
    enqueued_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    attempt_count: int = 0
    last_error: Optional[str] = None


class WriteQueue:

    def __init__(self, max_size: int, max_retries: int) -> None:
        self._queue: list[QueueItem] = []
        self._lock = threading.Lock()
        self._max_size = max_size
        self._max_retries = max_retries

    def enqueue(self, request: NewsWriteRequest) -> bool:
        """
        İsteği kuyruğa ekle.
        False → kuyruk dolu, dead-letter'a düşmeli.
        """
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
        with self._lock:
            batch = self._queue[:size]
            self._queue = self._queue[size:]
            return batch

    def requeue(self, item: QueueItem, error: str) -> bool:
        """
        Başarısız item'ı retry için geri ekle.
        max_retries aşıldıysa False → dead-letter'a gönder.
        """
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

        with self._lock:
            item.attempt_count += 1
            item.last_error = error
            self._queue.append(item)
            return True

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        return self.size == 0