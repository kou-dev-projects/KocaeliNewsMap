from __future__ import annotations

import secrets
import threading
import time
from collections import deque

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.scheduler import ScrapeOrchestrator
from app.settings import settings


router = APIRouter(prefix="/scrape", tags=["scrape"])

_RATE_LIMITER_LOCK = threading.Lock()
_RATE_LIMITER_STATE: dict[str, deque[float]] = {}


def _verify_trigger_auth(x_api_key: str | None) -> None:
    expected_key = settings.scrape_trigger_api_key
    if not expected_key:
        return

    if not x_api_key or not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="unauthorized_scrape_trigger")


def _resolve_client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",", 1)[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def _enforce_trigger_rate_limit(client_id: str, *, now_monotonic: float | None = None) -> None:
    if not settings.scrape_trigger_rate_limit_enabled:
        return

    max_requests = max(settings.scrape_trigger_rate_limit_requests, 1)
    window_seconds = max(settings.scrape_trigger_rate_limit_window_seconds, 1)
    now_value = now_monotonic if now_monotonic is not None else time.monotonic()
    threshold = now_value - window_seconds

    with _RATE_LIMITER_LOCK:
        bucket = _RATE_LIMITER_STATE.setdefault(client_id, deque())
        while bucket and bucket[0] <= threshold:
            bucket.popleft()

        if len(bucket) >= max_requests:
            retry_after = max(1, int(bucket[0] + window_seconds - now_value))
            raise HTTPException(
                status_code=429,
                detail="scrape_trigger_rate_limit_exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now_value)


@router.post("/trigger")
def trigger_scrape(
    request: Request,
    source: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    if not isinstance(x_api_key, str):
        x_api_key = None

    _verify_trigger_auth(x_api_key)
    _enforce_trigger_rate_limit(_resolve_client_id(request))

    orchestrator = ScrapeOrchestrator()

    try:
        if source:
            return orchestrator.crawl_source(source, trigger_type="manual")
        return orchestrator.crawl_active_sources(trigger_type="manual")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
