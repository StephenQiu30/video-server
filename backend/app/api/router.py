"""Top-level API router."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.native_openapi import router as native_openapi_router
from app.api.openapi import ERROR_RESPONSES
from app.api.routes.admin_ai_providers import router as admin_ai_providers_router
from app.api.routes.admin_downloads import router as admin_downloads_router
from app.api.routes.admin_files import router as admin_files_router
from app.api.routes.admin_providers import router as admin_providers_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.analyses import router as analyses_router
from app.api.routes.auth import router as auth_router
from app.api.routes.document_analyses import router as document_analyses_router
from app.api.routes.documents import router as documents_router
from app.api.routes.downloads import router as downloads_router
from app.api.routes.inspections import router as inspections_router
from app.api.routes.media_imports import router as media_imports_router
from app.api.routes.native_auth import router as native_auth_router
from app.api.routes.providers import router as providers_router
from app.api.routes.source_discoveries import router as source_discoveries_router
from app.api.routes.task_socket import router as task_socket_router
from app.api.routes.users import router as users_router

router = APIRouter()
router.include_router(health_router)
router.include_router(metrics_router)
router.include_router(native_auth_router)
router.include_router(native_openapi_router)

api_router = APIRouter(prefix="/api", responses=ERROR_RESPONSES)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(admin_users_router)
api_router.include_router(admin_downloads_router)
api_router.include_router(admin_files_router)
api_router.include_router(admin_ai_providers_router)
api_router.include_router(admin_providers_router)
api_router.include_router(inspections_router)
api_router.include_router(source_discoveries_router)
api_router.include_router(providers_router)
api_router.include_router(downloads_router)
api_router.include_router(documents_router)
api_router.include_router(document_analyses_router)
api_router.include_router(media_imports_router)
api_router.include_router(analyses_router)
api_router.include_router(task_socket_router)
router.include_router(api_router)
