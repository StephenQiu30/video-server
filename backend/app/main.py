"""FastAPI process entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.errors import app_error_handler, validation_error_handler
from app.api.middleware import request_guard
from app.api.openapi import API_DESCRIPTION, OPENAPI_TAGS, SWAGGER_UI_PARAMETERS
from app.api.quota_errors import quota_error_handler
from app.api.router import router
from app.application.quotas import QuotaExceeded
from app.composition import ApiRuntime, build_api_runtime
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.infrastructure.media_runner_factory import operator_provider_keys
from app.infrastructure.provider_status import current_provider_statuses


def create_app(
    settings: Settings | None = None,
    runtime: ApiRuntime | None = None,
) -> FastAPI:
    effective = settings or get_settings()
    owned_runtime = runtime is None and effective.app_env != "test"
    configured_runtime = build_api_runtime(effective) if owned_runtime else runtime

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            if owned_runtime and configured_runtime is not None:
                await configured_runtime.start()
            yield
        finally:
            if owned_runtime and configured_runtime is not None:
                await configured_runtime.close()

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
        lifespan=lifespan,
    )
    application.state.settings = effective
    application.state.provider_statuses = current_provider_statuses(
        operator_provider_keys(effective)
    )
    if configured_runtime is not None:
        application.state.auth_service = configured_runtime.auth_service
        application.state.user_service = configured_runtime.user_service
        application.state.download_use_cases = configured_runtime.use_cases
        application.state.analysis_use_cases = configured_runtime.analysis_use_cases
        application.state.media_import_use_cases = (
            configured_runtime.media_import_use_cases
        )
        application.state.document_import_use_cases = (
            configured_runtime.document_import_use_cases
        )
        application.state.source_discovery_use_cases = (
            configured_runtime.source_discovery_use_cases
        )
        application.state.rate_limiter = configured_runtime.rate_limiter
        application.state.readiness_probe = configured_runtime.readiness
        application.state.realtime_hub = configured_runtime.realtime_hub
        application.state.task_event_store = configured_runtime.task_event_store
        application.state.operational_metrics = configured_runtime.operational_metrics
        application.state.provider_status_service = (
            configured_runtime.provider_status_service
        )
        application.state.provider_catalog_service = (
            configured_runtime.provider_catalog_service
        )
        application.state.ai_provider_service = configured_runtime.ai_provider_service
        application.state.storage_file_service = configured_runtime.storage_file_service
        application.state.download_storage = configured_runtime.download_storage
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
