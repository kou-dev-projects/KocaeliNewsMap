from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

import redis
import redis.asyncio as aioredis

from app.db.database import db
from app.settings import settings

logger = logging.getLogger(__name__)

_SCRAPE_EVENT_STREAM_KEY = "pulse:scrape:events:v1"
_LATEST_SCRAPE_RUN_COLLECTION = "scrape_runs"
_LATEST_SCRAPE_RUN_ID = "latest"
_MAX_PERSISTED_SCRAPE_EVENTS = 500
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
        scrape_run_collection=None,
    ) -> None:
        self._redis_url = redis_url
        self._stream_maxlen = max(stream_maxlen, 100)
        self._redis: redis.Redis | None = redis_client
        self._scrape_run_collection = scrape_run_collection

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
        _persist_latest_scrape_event(event, collection=self._scrape_run_collection)
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


def _get_scrape_run_collection():
    return db[_LATEST_SCRAPE_RUN_COLLECTION]


def _normalize_event_details(details: dict[str, Any] | None) -> dict[str, Any]:
    return json.loads(json.dumps(details or {}, ensure_ascii=False, default=str))


def _serialize_scrape_event(event: ScrapeEvent) -> dict[str, Any]:
    return {
        "event": event.event,
        "message": event.message,
        "timestamp": float(event.timestamp),
        "job_id": event.job_id,
        "source": event.source,
        "trigger_type": event.trigger_type,
        "status": event.status,
        "attempt_count": event.attempt_count,
        "details": _normalize_event_details(event.details),
    }


def _build_latest_scrape_run_document(event: ScrapeEvent) -> dict[str, Any]:
    serialized_event = _serialize_scrape_event(event)
    timestamp = serialized_event["timestamp"]
    return {
        "_id": _LATEST_SCRAPE_RUN_ID,
        "job_id": event.job_id,
        "source": event.source,
        "trigger_type": event.trigger_type,
        "status": event.status,
        "started_at": timestamp,
        "updated_at": timestamp,
        "event_count": 1,
        "events": [serialized_event],
    }


def _persist_latest_scrape_event(event: ScrapeEvent, collection=None) -> None:
    if not event.job_id:
        return

    collection = collection or _get_scrape_run_collection()

    try:
        if event.event == "job_submitted":
            collection.replace_one(
                {"_id": _LATEST_SCRAPE_RUN_ID},
                _build_latest_scrape_run_document(event),
                upsert=True,
            )
            return

        current_run = collection.find_one(
            {"_id": _LATEST_SCRAPE_RUN_ID},
            {"job_id": 1, "started_at": 1, "status": 1},
        )

        if current_run is None:
            collection.replace_one(
                {"_id": _LATEST_SCRAPE_RUN_ID},
                _build_latest_scrape_run_document(event),
                upsert=True,
            )
            return

        if current_run.get("job_id") != event.job_id:
            if event.status in {"running", "completed", "failed", "cancelled"}:
                collection.replace_one(
                    {"_id": _LATEST_SCRAPE_RUN_ID},
                    _build_latest_scrape_run_document(event),
                    upsert=True,
                )
            return

        serialized_event = _serialize_scrape_event(event)
        collection.update_one(
            {"_id": _LATEST_SCRAPE_RUN_ID, "job_id": event.job_id},
            {
                "$set": {
                    "source": event.source,
                    "trigger_type": event.trigger_type,
                    "status": event.status,
                    "started_at": current_run.get("started_at", serialized_event["timestamp"]),
                    "updated_at": serialized_event["timestamp"],
                },
                "$push": {
                    "events": {
                        "$each": [serialized_event],
                        "$slice": -_MAX_PERSISTED_SCRAPE_EVENTS,
                    }
                },
                "$inc": {"event_count": 1},
            },
            upsert=False,
        )
    except Exception as exc:
        logger.warning(
            "scrape_events.persist_latest_failed",
            extra={"error": type(exc).__name__, "event": event.event},
        )


def get_latest_scrape_run() -> dict[str, Any] | None:
    try:
        document = _get_scrape_run_collection().find_one(
            {"_id": _LATEST_SCRAPE_RUN_ID},
            {"_id": 0},
        )
    except Exception as exc:
        logger.warning(
            "scrape_events.read_latest_failed",
            extra={"error": type(exc).__name__},
        )
        return None

    if document is None:
        return None

    document["events"] = [
        {
            "event": event.get("event"),
            "message": event.get("message"),
            "timestamp": event.get("timestamp"),
            "job_id": event.get("job_id"),
            "source": event.get("source"),
            "trigger_type": event.get("trigger_type"),
            "status": event.get("status"),
            "attempt_count": event.get("attempt_count"),
            "details": event.get("details") if isinstance(event.get("details"), dict) else {},
        }
        for event in document.get("events", [])
        if isinstance(event, dict)
    ]

    document["event_count"] = len(document["events"])
    return document


def get_recent_scrape_events_for_job(job_id: str, *, limit: int = 80) -> list[dict[str, Any]]:
    normalized_job_id = str(job_id or "").strip()
    if not normalized_job_id:
        return []

    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        items = client.xrevrange(
            _SCRAPE_EVENT_STREAM_KEY,
            count=max(limit * 8, 200),
        )
    except Exception as exc:
        logger.warning(
            "scrape_events.read_recent_failed",
            extra={"error": type(exc).__name__},
        )
        return []

    events: list[dict[str, Any]] = []
    for _msg_id, fields in items:
        if fields.get("job_id") != normalized_job_id:
            continue

        details_raw = fields.get("details")
        try:
            details = json.loads(details_raw) if details_raw else {}
        except (TypeError, json.JSONDecodeError):
            details = {}

        timestamp_raw = fields.get("timestamp")
        try:
            timestamp = float(timestamp_raw) if timestamp_raw is not None else None
        except (TypeError, ValueError):
            timestamp = None

        attempt_raw = fields.get("attempt_count")
        try:
            attempt_count = int(attempt_raw) if attempt_raw not in {None, ""} else None
        except (TypeError, ValueError):
            attempt_count = None

        events.append(
            {
                "event": fields.get("event"),
                "message": fields.get("message"),
                "timestamp": timestamp,
                "job_id": normalized_job_id,
                "source": fields.get("source") or None,
                "trigger_type": fields.get("trigger_type") or None,
                "status": fields.get("status") or None,
                "attempt_count": attempt_count,
                "details": details,
            }
        )
        if len(events) >= limit:
            break

    events.reverse()
    return events


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
