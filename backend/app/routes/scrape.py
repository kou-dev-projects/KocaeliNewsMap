from __future__ import annotations

import ipaddress
import json
import logging
import math
import re
import time

import redis
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.db.database import db
from app.services.scrape_orchestrator import (
    ScrapeTriggerResult,
    start_bootstrap_scrape_if_needed,
    start_refresh_scrape,
)
from app.services.scrape_events import (
    ScrapeEvent,
    ScrapeEventReader,
    _HEARTBEAT_SENTINEL,
    get_latest_scrape_run,
    get_recent_scrape_events_for_job,
    get_scrape_event_publisher,
)
from app.services.scrape_reset import reset_scraped_news_workspace
from app.settings import settings
from app.workers.job_manager import JobInfo, JobManager, JobQueueUnavailableError

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


def _build_job_response(
    request: Request,
    job_id: str,
    *,
    status: str = "pending",
) -> dict[str, str]:
    return {
        "job_id": job_id,
        "status": status,
        "status_url": str(request.url_for("get_job_status", job_id=job_id)),
    }


def _get_active_scrape_job(manager: JobManager) -> dict[str, str] | None:
    try:
        latest_job = manager.find_latest_active_job()
    except JobQueueUnavailableError:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc

    if latest_job is None:
        return None

    return {
        "job_id": latest_job.job_id,
        "status": latest_job.status,
        "source": latest_job.source or "",
        "trigger_type": latest_job.trigger_type,
    }


def _serialize_active_job_as_latest_run(
    job: JobInfo,
    recent_events: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    normalized_events = recent_events or []
    started_at = (
        normalized_events[0].get("timestamp")
        if normalized_events
        else job.started_at or job.created_at
    )
    updated_at = (
        normalized_events[-1].get("timestamp")
        if normalized_events
        else job.last_heartbeat_at or job.started_at or job.created_at
    )
    return {
        "job_id": job.job_id,
        "status": job.status,
        "source": job.source,
        "trigger_type": job.trigger_type,
        "started_at": started_at,
        "updated_at": updated_at,
        "event_count": len(normalized_events),
        "events": normalized_events,
    }


def _build_idle_latest_run() -> dict[str, object]:
    return {
        "job_id": None,
        "status": "idle",
        "source": None,
        "trigger_type": None,
        "started_at": None,
        "updated_at": None,
        "event_count": 0,
        "events": [],
    }


def _active_job_response(
    request: Request,
    *,
    active_job: dict[str, str],
) -> JSONResponse:
    content = _build_job_response(
        request,
        active_job["job_id"],
        status=active_job["status"],
    )
    content["reason"] = "job_already_running"
    content["source"] = active_job.get("source") or None
    content["trigger_type"] = active_job.get("trigger_type") or None
    return JSONResponse(status_code=200, content=content)


def _publish_scrape_job_submitted(
    *,
    job_id: str,
    source: str | None,
    trigger_type: str,
    message: str,
    details: dict | None = None,
) -> None:
    get_scrape_event_publisher().publish(
        ScrapeEvent(
            event="job_submitted",
            message=message,
            job_id=job_id,
            source=source,
            trigger_type=trigger_type,
            status="pending",
            details=details,
        )
    )


def _trigger_started_response(
    request: Request,
    *,
    result: ScrapeTriggerResult,
    source: str | None = None,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    if result.job_id is None:
        raise RuntimeError("missing_job_id_for_started_trigger")

    _publish_scrape_job_submitted(
        job_id=result.job_id,
        source=source,
        trigger_type=result.trigger_type,
        message=message,
        details=details,
    )

    content = _build_job_response(request, result.job_id)
    if details:
        content["details"] = details

    return JSONResponse(status_code=202, content=content)


def _build_job_snapshot_content(request: Request, job: JobInfo) -> dict[str, object]:
    content = _build_job_response(request, job.job_id, status=job.status)
    content["source"] = job.source
    content["trigger_type"] = job.trigger_type
    content["cancel_requested"] = job.cancel_requested
    content["cancel_requested_at"] = job.cancel_requested_at
    return content


@router.post("/trigger")
def trigger_scrape(
    request: Request,
    source: str | None = Query(default=None),
) -> JSONResponse:
    normalized_source = _normalize_source(source)
    _enforce_rate_limit(_resolve_client_id(request))
    _validate_source_exists(normalized_source)

    manager = _get_job_manager()
    try:
        job_id = manager.submit_job(source=normalized_source, trigger_type="manual")
    except JobQueueUnavailableError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc

    return _trigger_started_response(
        request,
        result=ScrapeTriggerResult(
            status="started",
            trigger_type="manual",
            job_id=job_id,
        ),
        source=normalized_source,
        message="Manual scrape job queued",
    )


@router.post("/bootstrap")
def bootstrap_scrape(
    request: Request,
    reset: bool = Query(default=False),
) -> JSONResponse:
    _enforce_rate_limit(_resolve_client_id(request))
    manager = _get_job_manager()

    active_job = _get_active_scrape_job(manager)
    if active_job is not None:
        return _active_job_response(
            request,
            active_job=active_job,
        )

    should_reset = reset if isinstance(reset, bool) else False

    details: dict[str, dict[str, object]] | None = None
    if should_reset:
        reset_result = reset_scraped_news_workspace(db)
        details = {
            "reset": {
                "deleted_counts": reset_result.deleted_counts,
                "total_deleted": reset_result.total_deleted,
            }
        }

    try:
        result = start_bootstrap_scrape_if_needed(db, manager)
    except JobQueueUnavailableError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc

    if result.status == "already_initialized":
        get_scrape_event_publisher().publish(
            ScrapeEvent(
                event="bootstrap_skipped",
                message="Bootstrap scrape skipped because data already exists",
                trigger_type=result.trigger_type,
                status="skipped",
                details={"reason": result.reason},
            )
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": result.status,
                "reason": result.reason,
                **({"details": details} if details else {}),
            },
        )

    return _trigger_started_response(
        request,
        result=result,
        message="Bootstrap scrape job queued",
        details=details,
    )


@router.post("/refresh")
def refresh_scrape(
    request: Request,
) -> JSONResponse:
    _enforce_rate_limit(_resolve_client_id(request))

    manager = _get_job_manager()
    active_job = _get_active_scrape_job(manager)
    if active_job is not None:
        return _active_job_response(
            request,
            active_job=active_job,
        )

    try:
        result = start_refresh_scrape(db, manager)
    except JobQueueUnavailableError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc

    return _trigger_started_response(
        request,
        result=result,
        message="Refresh scrape job queued",
    )


@router.post("/reset")
def reset_scrape_workspace(
    request: Request,
) -> JSONResponse:
    _enforce_rate_limit(_resolve_client_id(request))

    manager = _get_job_manager()
    active_job = _get_active_scrape_job(manager)
    if active_job is not None:
        raise HTTPException(status_code=409, detail="scrape_job_running_reset_blocked")

    reset_result = reset_scraped_news_workspace(db)
    get_scrape_event_publisher().publish(
        ScrapeEvent(
            event="workspace_reset_manual",
            message="Scrape workspace cleared manually",
            trigger_type="manual",
            status="completed",
            details={
                "deleted_counts": reset_result.deleted_counts,
                "total_deleted": reset_result.total_deleted,
            },
        )
    )
    return JSONResponse(
        status_code=200,
        content={
            "status": "completed",
            "deleted_counts": reset_result.deleted_counts,
            "total_deleted": reset_result.total_deleted,
        },
    )


@router.post("/stop")
def stop_scrape(
    request: Request,
    job_id: str | None = Query(default=None),
) -> JSONResponse:
    _enforce_rate_limit(_resolve_client_id(request))
    manager = _get_job_manager()

    target_job: JobInfo | None = None
    normalized_job_id = str(job_id or "").strip() or None
    if normalized_job_id:
        try:
            target_job = manager.get_job(normalized_job_id)
        except JobQueueUnavailableError as exc:
            raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
        if target_job is None:
            raise HTTPException(status_code=404, detail="job_not_found")
        if target_job.status not in {"pending", "running"}:
            raise HTTPException(status_code=409, detail="job_not_active")
    else:
        active_job = _get_active_scrape_job(manager)
        if active_job is None:
            raise HTTPException(status_code=404, detail="active_job_not_found")
        try:
            target_job = manager.get_job(active_job["job_id"])
        except JobQueueUnavailableError as exc:
            raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
        if target_job is None:
            raise HTTPException(status_code=404, detail="job_not_found")

    if target_job.cancel_requested:
        return JSONResponse(
            status_code=200,
            content=_build_job_snapshot_content(request, target_job),
        )

    try:
        cancelled_job = manager.request_cancel(target_job.job_id, base_job=target_job)
    except JobQueueUnavailableError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="job_queue_unavailable") from exc

    get_scrape_event_publisher().publish(
        ScrapeEvent(
            event="job_cancelling",
            message="Scrape stop requested",
            job_id=cancelled_job.job_id,
            source=cancelled_job.source,
            trigger_type=cancelled_job.trigger_type,
            status="running",
            details={
                "cancel_requested": True,
                "cancel_requested_at": cancelled_job.cancel_requested_at,
            },
        )
    )

    return JSONResponse(
        status_code=202,
        content=_build_job_snapshot_content(request, cancelled_job),
    )


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
) -> dict:
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
    response["cancel_requested"] = job.cancel_requested
    if job.cancel_requested_at is not None:
        response["cancel_requested_at"] = job.cancel_requested_at
    if job.result is not None:
        response["result"] = job.result
    if job.error is not None:
        response["error"] = job.error

    return response


@router.get("/latest")
def get_latest_scrape() -> dict:
    latest_run = get_latest_scrape_run()
    manager = _get_job_manager()

    try:
        active_job = manager.find_latest_active_job()
    except (JobQueueUnavailableError, RuntimeError):
        if latest_run is None:
            return _build_idle_latest_run()
        return latest_run

    if active_job is not None:
        if latest_run is None or latest_run.get("job_id") != active_job.job_id:
            return _serialize_active_job_as_latest_run(
                active_job,
                recent_events=get_recent_scrape_events_for_job(active_job.job_id),
            )
    elif latest_run is not None and latest_run.get("status") in {"pending", "running"}:
        return _build_idle_latest_run()

    if latest_run is None:
        return _build_idle_latest_run()

    return latest_run


@router.get("/events")
async def scrape_events_stream(
    request: Request,
    job_id: str | None = Query(default=None, description="Filter events to a specific job ID"),
) -> StreamingResponse:
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
