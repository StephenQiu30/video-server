import shutil

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas import HealthResponse
from app.services.storage import ObjectStorage

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=get_settings().app_name)


@router.get("/ready")
def ready() -> JSONResponse:
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "storage": _check_storage(),
        "media_tools": _check_media_tools(),
    }
    ok = all(item["ok"] for item in checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )


def _check_database() -> dict[str, str | bool]:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}


def _check_redis() -> dict[str, str | bool]:
    try:
        Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}


def _check_storage() -> dict[str, str | bool]:
    try:
        ObjectStorage().ensure_bucket()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}


def _check_media_tools() -> dict[str, str | bool]:
    ffmpeg_found = shutil.which("ffmpeg") is not None
    ffprobe_found = shutil.which("ffprobe") is not None
    ok = ffmpeg_found and ffprobe_found
    if ok:
        return {"ok": True, "ffmpeg": True, "ffprobe": True}
    return {
        "ok": False,
        "ffmpeg": ffmpeg_found,
        "ffprobe": ffprobe_found,
        "message": "MVP 本地验收需要安装 ffmpeg / ffprobe",
    }
