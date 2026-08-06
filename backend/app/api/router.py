"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes.analyses import router as analyses_router
from app.api.routes.downloads import router as downloads_router
from app.api.routes.health import router as health_router
from app.api.routes.inspections import router as inspections_router

router = APIRouter()
router.include_router(health_router)
router.include_router(inspections_router)
router.include_router(downloads_router)
router.include_router(analyses_router)
