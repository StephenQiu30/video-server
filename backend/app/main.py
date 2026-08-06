"""FastAPI process entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import app_error_handler
from app.api.router import router
from app.composition import ApiRuntime, build_api_runtime
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.web.spa import mount_frontend


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
            yield
        finally:
            if owned_runtime and configured_runtime is not None:
                await configured_runtime.close()

    application = FastAPI(
        title="Universal Video Downloader API",
        version=effective.app_version,
        lifespan=lifespan,
    )
    application.state.settings = effective
    if configured_runtime is not None:
        application.state.download_use_cases = configured_runtime.use_cases
        application.state.analysis_use_cases = configured_runtime.analysis_use_cases
        application.state.readiness_probe = configured_runtime.readiness
    application.include_router(router)
    application.add_exception_handler(AppError, app_error_handler)
    mount_frontend(application, effective.frontend_dist_dir)
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
    )


if __name__ == "__main__":
    run()
