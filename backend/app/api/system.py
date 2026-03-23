from fastapi import APIRouter

from app.settings import settings

router = APIRouter(tags=["system"])


@router.get("/info")
def info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@router.get("/health")
def health():
    return {
        "status": "ok",
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }
