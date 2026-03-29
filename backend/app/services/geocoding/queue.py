from __future__ import annotations
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .schemas import GeocodingInput

logger = logging.getLogger(__name__)


@dataclass
class PendingGeocodingItem:
    input_data: GeocodingInput
    enqueued_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    attempt_count: int = 0
    last_error: Optional[str] = None


class GeocodingQueue:
 
    _MAX_SIZE = 500
    _MAX_RETRIES = 3

    def __init__(self) -> None:
        self._queue: list[PendingGeocodingItem] = []
        self._lock = threading.Lock()

    def enqueue(self, input_data: GeocodingInput, reason: str) -> bool:
       
        with self._lock:
            if len(self._queue) >= self._MAX_SIZE:
                logger.error(
                    "geocoding.queue.full",
                    extra={
                        "size": self._MAX_SIZE,
                        "dropped_address": input_data.address[:60],
                        "reason": reason,
                    },
                )
                return False
            self._queue.append(PendingGeocodingItem(input_data=input_data))
            logger.info(
                "geocoding.queue.enqueued",
                extra={
                    "address": input_data.address[:60],
                    "reason": reason,
                    "queue_size": len(self._queue),
                },
            )
            return True

    def dequeue_batch(self, size: int = 10) -> list[PendingGeocodingItem]:
        with self._lock:
            batch = self._queue[:size]
            self._queue = self._queue[size:]
            return batch

    def requeue(self, item: PendingGeocodingItem, error: str) -> None:
        if item.attempt_count >= self._MAX_RETRIES:
            logger.warning(
                "geocoding.queue.max_retries_exceeded",
                extra={
                    "address": item.input_data.address[:60],
                    "attempts": item.attempt_count,
                    "last_error": error[:100],
                },
            )
            return
        with self._lock:
            item.attempt_count += 1
            item.last_error = error
            self._queue.append(item)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        return self.size == 0