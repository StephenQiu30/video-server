"""FastAPI process entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.v1.downloads import router as downloads_router
from src.api.v1.health import router as health_router
from src.api.v1.media import router as media_router
from src.core.config import Settings, get_settings
from src.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from src.core.logging import configure_logging, get_logger
from src.db.session import get_session_factory
from src.downloads.application import DownloadApplicationService
from src.media.service import MediaInspectionService
from src.media.yt_dlp import YtdlpExtractor
from src.minio_client import MinioStorage
from src.rabbitmq import RabbitMQPublisher

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an app, optionally with explicit settings for tests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        effective = settings or get_settings()
        app.state.settings = effective
        configure_logging(effective.log_level)
        engine: AsyncEngine | None = None
        if settings is None:
            session_factory = get_session_factory()
        else:
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)
            session_factory = async_sessionmaker(
                engine, expire_on_commit=False, autoflush=False
            )
        publisher = RabbitMQPublisher(effective)
        storage = MinioStorage(effective)
        extractor = YtdlpExtractor(
            allowed_extractors=effective.ytdlp_allowed_extractors,
            timeout_seconds=effective.inspect_timeout_seconds,
            max_duration_seconds=effective.max_video_duration_seconds,
        )
        app.state.rabbitmq_publisher = publisher
        app.state.minio_storage = storage
        app.state.media_service = MediaInspectionService(
            session_factory,
            extractor,
            inspect_ttl_seconds=effective.inspect_ttl_seconds,
        )
        app.state.download_service = DownloadApplicationService(
            session_factory, storage, effective
        )

        async def readiness_checker() -> dict[str, Any]:
            database = False
            rabbitmq = publisher.connection is not None
            minio = False
            try:
                async with session_factory() as session:
                    await session.execute(text("SELECT 1"))
                database = True
            except Exception:
                database = False
            try:
                minio = await storage.healthcheck()
            except Exception:
                minio = False
            ready = database and rabbitmq and minio
            return {
                "status": "ok" if ready else "not_ready",
                "dependencies": {
                    "database": "ok" if database else "unavailable",
                    "rabbitmq": "ok" if rabbitmq else "unavailable",
                    "minio": "ok" if minio else "unavailable",
                },
            }

        app.state.readiness_checker = readiness_checker
        try:
            await publisher.connect()
        except Exception:
            logger.error("rabbitmq_connect_failed", extra={"dependency": "rabbitmq"})
        try:
            await storage.ensure_bucket()
        except Exception:
            logger.error("minio_bucket_init_failed", extra={"dependency": "minio"})
        logger.info("api_started", extra={"app_env": effective.app_env})
        try:
            yield
        finally:
            await publisher.close()
            if engine is not None:
                await engine.dispose()
            logger.info("api_stopped")

    app = FastAPI(
        title="Video Downloader API",
        version=(settings.app_version if settings else "0.1.0"),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        # The module-level app must be importable before environment loading;
        # the lifespan replaces this default with the typed Settings object.
        allow_origins=[settings.web_origin if settings else "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    # Include the concrete routers directly.  FastAPI 0.115 keeps nested
    # ``_IncludedRouter`` nodes in OpenAPI when an APIRouter includes another
    # APIRouter, so flattening here preserves the six public operations.
    app.include_router(media_router)
    app.include_router(downloads_router)
    app.include_router(health_router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/healthz", tags=["system"])
    async def healthz(_request: Request) -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    runtime_settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=runtime_settings.app_host,
        port=runtime_settings.app_port,
        reload=False,
    )
