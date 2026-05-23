import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.db.upgrade import run_database_upgrades
from app import models  # noqa: F401
from app.routers import admin, auth, health, metrics, parse, tasks


@asynccontextmanager
async def _app_lifespan(settings: "Settings"):
    logger = logging.getLogger(__name__)
    try:
        if settings.skip_db_bootstrap and settings.app_env != "production":
            logger.warning("skip_db_bootstrap 已开启，跳过数据库建表与迁移。")
        else:
            Base.metadata.create_all(bind=engine)
            run_database_upgrades(engine)
    except Exception as exc:  # pragma: no cover
        logger.warning("数据库初始化失败，将继续启动：%s", exc)
        if settings.app_env == "production" and not settings.skip_db_bootstrap:
            raise

    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logger = logging.getLogger(__name__)
    setup_logging(settings.app_env)
    app = FastAPI(title=settings.app_name, lifespan=lambda app_obj: _app_lifespan(settings))
    app.add_exception_handler(AppError, app_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Routers
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(parse.router)
    app.include_router(tasks.router)
    app.include_router(admin.router)
    app.include_router(metrics.router)

    return app


app = create_app()
