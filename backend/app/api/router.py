from fastapi import APIRouter

from .system import router as system_router

router = APIRouter(prefix="/api/v1")
router.include_router(system_router)
