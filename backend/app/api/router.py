from fastapi import APIRouter

from app.routes import news_router
from .system import router as system_router

router = APIRouter(prefix="/api/v1")
router.include_router(system_router)
router.include_router(news_router)
