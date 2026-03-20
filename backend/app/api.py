from fastapi import APIRouter

from app.settings import settings


router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/info")
def info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }
