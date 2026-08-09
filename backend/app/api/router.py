"""Top-level API router."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.openapi import ERROR_RESPONSES
from app.api.routes.analyses import router as analyses_router
from app.api.routes.auth import router as auth_router
from app.api.routes.downloads import router as downloads_router
from app.api.routes.inspections import router as inspections_router

router = APIRouter()
router.include_router(health_router)

api_router = APIRouter(prefix="/api", responses=ERROR_RESPONSES)
api_router.include_router(auth_router)
api_router.include_router(inspections_router)
api_router.include_router(downloads_router)
api_router.include_router(analyses_router)
router.include_router(api_router)
