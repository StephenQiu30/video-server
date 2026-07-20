"""Single composition point for the six fixed MVP operations."""

from fastapi import APIRouter

from src.api.v1.downloads import router as downloads_router
from src.api.v1.health import router as health_router
from src.api.v1.media import router as media_router

router = APIRouter()
router.include_router(media_router)
router.include_router(downloads_router)
router.include_router(health_router)

__all__ = ["router"]
