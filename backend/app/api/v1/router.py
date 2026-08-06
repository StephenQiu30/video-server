"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1.routes.analyses import router as analyses_router
from app.api.v1.routes.downloads import router as downloads_router
from app.api.v1.routes.inspections import router as inspections_router

router = APIRouter(prefix="/api/v1")
router.include_router(inspections_router)
router.include_router(downloads_router)
router.include_router(analyses_router)
