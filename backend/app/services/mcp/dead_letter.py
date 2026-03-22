from __future__ import annotations
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .schemas import NewsWriteRequest

logger = logging.getLogger(__name__)


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

    def __init__(self) -> None:
        self._items: list[DeadLetterItem] = []
        self._lock = threading.Lock()

    def add(
        self,
        request: NewsWriteRequest,
        error: str,
        attempt_count: int,
    ) -> None:
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
        with self._lock:
            return list(self._items)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._items)