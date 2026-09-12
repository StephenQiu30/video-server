"""FastAPI process entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.errors import app_error_handler, validation_error_handler
from app.api.middleware import request_guard
from app.api.openapi import API_DESCRIPTION, OPENAPI_TAGS, SWAGGER_UI_PARAMETERS
from app.api.quota_errors import quota_error_handler
from app.api.router import router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.integrations.media_runner_factory import operator_provider_keys
from app.integrations.provider_status import current_provider_statuses
from app.lifespan import api_lifespan
from app.runtime import ApiRuntime, ApiServices
from app.services.quotas import QuotaExceeded


def create_app(
    settings: Settings | None = None,
    runtime: ApiRuntime | None = None,
) -> FastAPI:
    effective = settings or get_settings()
    application = FastAPI(
        title="视频下载与分析服务 API",
        description=API_DESCRIPTION,
        docs_url="/docs",
        license_info={"name": "MIT", "identifier": "MIT"},
        openapi_tags=OPENAPI_TAGS,
        openapi_url="/openapi.json",
        redoc_url="/redoc",
        swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
        version=effective.app_version,
        lifespan=lambda application: api_lifespan(application, effective, runtime),
    )
    application.state.settings = effective
    application.state.provider_statuses = current_provider_statuses(
        operator_provider_keys(effective), effective.runner_default_access_policies
    )
    application.state.services = runtime.services if runtime else ApiServices()
    application.include_router(router)
    application.middleware("http")(
        lambda request, call_next: request_guard(
            request,
            call_next,
            max_body_bytes=effective.request_max_bytes,
            timeout_seconds=effective.request_timeout_seconds,
            production=effective.app_env == "production",
            connect_origins=(
                (effective.minio_public_origin(),)
                if effective.media_import_enabled or effective.document_import_enabled
                else ()
            ),
            media_origins=(
                (effective.minio_public_origin(),)
                if effective.media_import_enabled
                else ()
            ),
        )
    )
    application.add_exception_handler(QuotaExceeded, quota_error_handler)
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    return application


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
        proxy_headers=False,
    )


if __name__ == "__main__":
    run()
