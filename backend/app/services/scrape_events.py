from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import redis
import redis.asyncio as aioredis

from app.settings import settings

logger = logging.getLogger(__name__)

_SCRAPE_EVENT_STREAM_KEY = "pulse:scrape:events:v1"
_publisher: "ScrapeEventPublisher | None" = None


@dataclass
class ScrapeEvent:
    event: str
    message: str
    timestamp: float = field(default_factory=time.time)
    job_id: Optional[str] = None
    source: Optional[str] = None
    trigger_type: Optional[str] = None
    status: Optional[str] = None
    attempt_count: Optional[int] = None
    details: Optional[dict[str, Any]] = None




class ScrapeEventPublisher:
    def __init__(
        self,
        redis_url: str,
        stream_maxlen: int,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self._redis_url = redis_url
        self._stream_maxlen = max(stream_maxlen, 100)
        self._redis: redis.Redis | None = redis_client

    def _connect(self) -> redis.Redis | None:
        try:
            client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            self._redis = client
        except Exception as exc:
            logger.warning(
                "scrape_events.redis_unavailable",
                extra={"error": type(exc).__name__},
            )
            self._redis = None
        return self._redis

    def _get_redis(self) -> redis.Redis | None:
        if self._redis is None:
            return self._connect()
        return self._redis

    def publish(self, event: ScrapeEvent) -> None:
        client = self._get_redis()
        if client is None:
            return

        payload = {
            "event": event.event,
            "message": event.message,
            "timestamp": str(event.timestamp),
            "job_id": event.job_id or "",
            "source": event.source or "",
            "trigger_type": event.trigger_type or "",
            "status": event.status or "",
            "attempt_count": "" if event.attempt_count is None else str(event.attempt_count),
            "details": json.dumps(event.details or {}, ensure_ascii=False, default=str),
        }

        try:
            client.xadd(
                _SCRAPE_EVENT_STREAM_KEY,
                payload,
                maxlen=self._stream_maxlen,
                approximate=True,
            )
        except Exception as exc:
            logger.warning(
                "scrape_events.publish_failed",
                extra={"error": type(exc).__name__, "event": event.event},
            )
            self._redis = None


def get_scrape_event_publisher() -> ScrapeEventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = ScrapeEventPublisher(
            redis_url=settings.redis_url,
            stream_maxlen=settings.scrape_event_stream_maxlen,
        )
    return _publisher




_HEARTBEAT_SENTINEL = ":heartbeat"

_XREAD_BLOCK_MS = 3_000


class ScrapeEventReader:
    """Async Redis Stream reader for SSE consumers.

    Usage::
        reader = ScrapeEventReader(settings.redis_url)
        async for msg_id, fields in reader.stream(last_id="$"):
            if msg_id == _HEARTBEAT_SENTINEL:
                yield ": ping\\n\\n"
            else:
                yield format_sse(msg_id, fields)
    """


    _MAX_CONSECUTIVE_ERRORS = 5

    def __init__(
        self,
        redis_url: str,
        stream_key: str = _SCRAPE_EVENT_STREAM_KEY,
        heartbeat_seconds: float = 15.0,
    ) -> None:
        self._redis_url = redis_url
        self._stream_key = stream_key
        self._heartbeat_seconds = max(heartbeat_seconds, 1.0)

    def _create_client(self):
        return aioredis.from_url(
            self._redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=None,
        )

    async def stream(
        self,
        *,
        last_id: str = "$",
        job_id_filter: str | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, str]]]:
       
        client = self._create_client()
        current_id = last_id
        last_heartbeat = time.monotonic()
        consecutive_errors = 0

        try:
            while True:
                now = time.monotonic()
                if now - last_heartbeat >= self._heartbeat_seconds:
                    yield _HEARTBEAT_SENTINEL, {}
                    last_heartbeat = time.monotonic()

                try:
                    result = await client.xread(
                        streams={self._stream_key: current_id},
                        count=10,
                        block=_XREAD_BLOCK_MS,
                    )
                except asyncio.CancelledError:
                    raise  
                except Exception as exc:
                    consecutive_errors += 1
                    logger.warning(
                        "scrape_events.reader_error",
                        extra={
                            "error": type(exc).__name__,
                            "consecutive_errors": consecutive_errors,
                            "current_id": current_id,
                        },
                    )
                    try:
                        await client.aclose()
                    except Exception:
                        pass
                    await asyncio.sleep(2)
                    client = self._create_client()

                    if consecutive_errors >= self._MAX_CONSECUTIVE_ERRORS:
                        logger.warning(
                            "scrape_events.reader_cursor_reset",
                            extra={"old_id": current_id},
                        )
                        current_id = "$"
                        consecutive_errors = 0
                    continue

                consecutive_errors = 0

                if not result:
                    continue

                _stream_name, entries = result[0]
                for msg_id, fields in entries:
                    current_id = msg_id  # advance cursor
                    if job_id_filter and fields.get("job_id") != job_id_filter:
                        continue
                    yield msg_id, fields
                    last_heartbeat = time.monotonic()

        except asyncio.CancelledError:
            pass  
        finally:
            try:
                await client.aclose()
            except Exception:
                pass
