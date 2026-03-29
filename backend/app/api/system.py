from __future__ import annotations

import secrets
from typing import Any

import redis
from fastapi import APIRouter, Header, HTTPException, Response, status

from app.db.database import db
from app.settings import settings

router = APIRouter(tags=["system"])

_REDIS_HEALTH_CLIENT: redis.Redis | None = None


def _get_redis_health_client() -> redis.Redis:
    global _REDIS_HEALTH_CLIENT
    if _REDIS_HEALTH_CLIENT is None:
        _REDIS_HEALTH_CLIENT = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _REDIS_HEALTH_CLIENT


def _check_mongo() -> bool:
    try:
        db.command("ping")
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        _get_redis_health_client().ping()
        return True
    except Exception:
        return False


@router.get("/info")
def info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@router.get("/livez")
def livez():
    return {"status": "ok"}


@router.get("/readyz")
def readyz(response: Response):
    mongo_ok = _check_mongo()
    redis_ok = _check_redis()
    ready = mongo_ok and redis_ok

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "checks": {
            "mongo": "ok" if mongo_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }


@router.get("/diagnostics")
def diagnostics(
    response: Response,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _authorize_diagnostics(x_api_key)

    mongo_ok, mongo_error = _check_mongo_detailed()
    redis_ok, redis_error = _check_redis_detailed()
    ready = mongo_ok and redis_ok

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    checks: dict[str, Any] = {
        "mongo": {"status": "ok" if mongo_ok else "error"},
        "redis": {"status": "ok" if redis_ok else "error"},
    }
    if mongo_error:
        checks["mongo"]["error"] = mongo_error
    if redis_error:
        checks["redis"]["error"] = redis_error

    return {
        "status": "ok" if ready else "degraded",
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "checks": checks,
    }


def _authorize_diagnostics(api_key: str | None) -> None:
    if settings.app_env not in ("production", "prod"):
        return

    expected_key = settings.scrape_trigger_api_key
    if expected_key and api_key and secrets.compare_digest(api_key, expected_key):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="diagnostics_access_denied",
    )


def _check_mongo_detailed() -> tuple[bool, str | None]:
    try:
        db.command("ping")
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _check_redis_detailed() -> tuple[bool, str | None]:
    try:
        _get_redis_health_client().ping()
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
