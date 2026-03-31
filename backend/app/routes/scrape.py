from __future__ import annotations

import ipaddress
import json
import logging
import math
import re
import secrets
import time

import redis
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.db.database import db
from app.services.scrape_events import (
    ScrapeEvent,
    ScrapeEventReader,
    _HEARTBEAT_SENTINEL,
    get_scrape_event_publisher,
)
from app.settings import settings
from app.workers.job_manager import JobManager, JobQueueUnavailableError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["scrape"])

_job_manager: JobManager | None = None
_rate_limit_redis: redis.Redis | None = None
_trusted_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] | None = None

_RATE_LIMIT_KEY_PREFIX = "pulse:ratelimit:trigger"

_STREAM_ID_RE = re.compile(r"^(?:\$|0|\d{1,15}(?:-\d{1,19})?)$")


def _parse_last_event_id(raw: str) -> str:
    """Return a valid Redis Stream ID or "$" as safe fallback."""
    stripped = raw.strip()
    if _STREAM_ID_RE.match(stripped):
        return stripped
    logger.warning("scrape.events.invalid_last_event_id", extra={"raw": stripped[:100]})
    return "$"


def _get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def _get_rate_limit_redis() -> redis.Redis | None:
    global _rate_limit_redis
    if _rate_limit_redis is None:
        try:
            _rate_limit_redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            _rate_limit_redis.ping()
        except Exception:
            _rate_limit_redis = None
    return _rate_limit_redis


def _get_trusted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    global _trusted_networks
    if _trusted_networks is None:
        _trusted_networks = []
        raw = settings.trusted_proxy_cidrs
        if raw:
            for cidr in raw.split(","):
                cidr = cidr.strip()
                if cidr:
                    try:
                        _trusted_networks.append(ipaddress.ip_network(cidr, strict=False))
                    except ValueError:
                        logger.warning("scrape.invalid_trusted_cidr", extra={"cidr": cidr})
    return _trusted_networks


def _verify_trigger_auth(x_api_key: str | None) -> None:
    expected_key = settings.scrape_trigger_api_key
    if not expected_key:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="unauthorized_scrape_trigger")


def _normalize_source(source: str | None) -> str | None:
    if not isinstance(source, str):
        return None

    normalized = source.strip().lower()
    return normalized or None


def _validate_source_exists(source: str | None) -> None:
    if source is None:
        return

    try:
        exists = db["sources"].find_one(
            {"domain": source, "active": True},
            {"_id": 1},
        )
    except Exception as exc:
        logger.warning(
            "scrape.source_validation_failed",
            extra={"source": source, "error": type(exc).__name__},
        )
        raise HTTPException(status_code=503, detail="source_validation_unavailable") from exc

    if exists is None:
        raise HTTPException(status_code=404, detail=f"active_source_not_found: {source}")


def _resolve_client_id(request: Request) -> str:
    peer_ip = request.client.host if request.client else "unknown"
    trusted = _get_trusted_networks()

    if trusted and peer_ip != "unknown":
        try:
            peer_addr = ipaddress.ip_address(peer_ip)
            is_trusted = any(peer_addr in net for net in trusted)
        except ValueError:
            is_trusted = False

        if is_trusted:
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                first = forwarded_for.split(",", 1)[0].strip()
                if first:
                    return first

    return peer_ip


def _enforce_rate_limit(client_id: str) -> None:
    global _rate_limit_redis
    if not settings.scrape_trigger_rate_limit_enabled:
        return

    redis_client = _get_rate_limit_redis()
    if redis_client is None:
        return

    max_requests = max(settings.scrape_trigger_rate_limit_requests, 1)
    window_seconds = max(settings.scrape_trigger_rate_limit_window_seconds, 1)
    now = time.time()
    window_start = now - window_seconds
    key = f"{_RATE_LIMIT_KEY_PREFIX}:{client_id}"

    try:
        pipe = redis_client.pipeline(transaction=True)
        pipe.zremrangebyscore(key, "-inf", window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 1)
        results = pipe.execute()

        current_count = results[1]
        if current_count >= max_requests:
            redis_client.zrem(key, str(now))

            oldest = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest:
                _, oldest_score = oldest[0]
                retry_after = max(1, math.ceil(oldest_score + window_seconds - now))
            else:
                retry_after = window_seconds

            raise HTTPException(
                status_code=429,
                detail="scrape_trigger_rate_limit_exceeded",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception:
        _rate_limit_redis = None  # force reconnect on next call
        logger.warning("scrape.rate_limit.redis_error - failing open")


@router.post("/trigger")
def trigger_scrape(
    request: Request,
    source: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> JSONResponse:
    if not isinstance(x_api_key, str):
        x_api_key = None

    normalized_source = _normalize_source(source)
    _verify_trigger_auth(x_api_key)
    _enforce_rate_limit(_resolve_client_id(request))
    _validate_source_exists(normalized_source)

    manager = _get_job_manager()
    try:
        job_id = manager.submit_job(source=normalized_source, trigger_type="manual")
    except JobQueueUnavailableError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc

    get_scrape_event_publisher().publish(
        ScrapeEvent(
            event="job_submitted",
            message="Manual scrape job queued",
            job_id=job_id,
            source=normalized_source,
            trigger_type="manual",
            status="pending",
        )
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "pending",
            "status_url": str(request.url_for("get_job_status", job_id=job_id)),
        },
    )


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    if not isinstance(x_api_key, str):
        x_api_key = None

    _verify_trigger_auth(x_api_key)

    manager = _get_job_manager()
    try:
        job = manager.get_job(job_id)
    except JobQueueUnavailableError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    if job is None:
        raise HTTPException(status_code=404, detail="job_not_found")

    response: dict = {
        "job_id": job.job_id,
        "status": job.status,
        "source": job.source,
        "trigger_type": job.trigger_type,
        "created_at": job.created_at,
        "attempt_count": job.attempt_count,
    }

    if job.started_at is not None:
        response["started_at"] = job.started_at
    if job.completed_at is not None:
        response["completed_at"] = job.completed_at
    if job.last_heartbeat_at is not None:
        response["last_heartbeat_at"] = job.last_heartbeat_at
    if job.result is not None:
        response["result"] = job.result
    if job.error is not None:
        response["error"] = job.error

    return response


@router.get("/events")
async def scrape_events_stream(
    request: Request,
    job_id: str | None = Query(default=None, description="Filter events to a specific job ID"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> StreamingResponse:

    if not isinstance(x_api_key, str):
        x_api_key = None
    _verify_trigger_auth(x_api_key)

    last_event_id = _parse_last_event_id(request.headers.get("last-event-id", ""))

    job_id_filter: str | None = None
    if isinstance(job_id, str):
        job_id_filter = job_id.strip().lower() or None

    reader = ScrapeEventReader(
        redis_url=settings.redis_url,
        heartbeat_seconds=settings.scrape_events_heartbeat_seconds,
    )

    async def _generate():
        async for msg_id, fields in reader.stream(
            last_id=last_event_id,
            job_id_filter=job_id_filter,
        ):
            if await request.is_disconnected():
                break

            if msg_id == _HEARTBEAT_SENTINEL:
                yield ": ping\n\n"
                continue

            out: dict = dict(fields)
            if out.get("details"):
                try:
                    out["details"] = json.loads(out["details"])
                except (json.JSONDecodeError, TypeError):
                    pass
            if out.get("attempt_count"):
                try:
                    out["attempt_count"] = int(out["attempt_count"])
                except (ValueError, TypeError):
                    pass
            if out.get("timestamp"):
                try:
                    out["timestamp"] = float(out["timestamp"])
                except (ValueError, TypeError):
                    pass

            payload = json.dumps(out, ensure_ascii=False, default=str)
            event_name = out.get("event", "message")
            yield f"id: {msg_id}\nevent: {event_name}\ndata: {payload}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
