from __future__ import annotations

from typing import Any

import redis
from fastapi import APIRouter, Response, status

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


def _check_mongo() -> tuple[bool, str | None]:
    try:
        db.command("ping")
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _check_redis() -> tuple[bool, str | None]:
    try:
        _get_redis_health_client().ping()
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


@router.get("/info")
def info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@router.get("/health")
def health(response: Response):
    mongo_ok, mongo_error = _check_mongo()
    redis_ok, redis_error = _check_redis()
    ready = mongo_ok and redis_ok

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    checks: dict[str, Any] = {
        "mongo": {
            "status": "ok" if mongo_ok else "error",
        },
        "redis": {
            "status": "ok" if redis_ok else "error",
        },
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
