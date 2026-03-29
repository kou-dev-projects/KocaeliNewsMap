from fastapi import APIRouter

from app.routes.news import router as news_router
from app.routes.scrape import router as scrape_router
from .system import router as system_router

router = APIRouter(prefix="/api/v1")
router.include_router(system_router)
router.include_router(news_router)
router.include_router(scrape_router)
