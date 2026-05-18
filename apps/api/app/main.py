import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.db.upgrade import run_database_upgrades
from app import models  # noqa: F401
from app.routers import admin, auth, health, metrics, parse, tasks


@asynccontextmanager
def _app_lifespan(settings: "Settings"):
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

    # Static files and SPA routing
    # The 'static' directory should be in the app root (where main.py's parent's parent is)
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    if os.path.exists(static_dir):
        # Mount assets and other static files
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
        
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # 1. Check if the path is an API call - let it fall through to 404 if it is
            if full_path.startswith("api/") or full_path in ["health", "ready", "metrics"]:
                return {"detail": "Not Found"}
            
            # 2. Check if specific file exists in static dir
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            
            # 3. Fallback to index.html for SPA routing
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app


app = create_app()
