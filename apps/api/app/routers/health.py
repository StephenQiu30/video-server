from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis import Redis
from rq import Queue
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.schemas import HealthResponse, ReadinessResponse
from app.services.storage import ObjectStorage

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=get_settings().app_name)


@router.get("/ready", response_model=ReadinessResponse)
def ready() -> JSONResponse:
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "queue": _check_queue(),
        "queue_consumer": _check_queue_consumer(),
        "storage": _check_storage(),
        "media_tools": _check_media_tools(),
        "download_work_dir": _check_download_work_dir(),
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


def _check_queue() -> dict[str, str | int | bool]:
    try:
        from rq import Worker
        settings = get_settings()
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        queue = Queue(settings.rq_queue_name, connection=redis)
        workers = Worker.all(connection=redis)
        worker_count = len([w for w in workers if settings.rq_queue_name in w.queue_names()])
        return {
            "ok": worker_count > 0,
            "name": settings.rq_queue_name,
            "queued_jobs": len(queue),
            "workers": worker_count,
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}


def _check_queue_consumer() -> dict[str, str | bool]:
    try:
        import app.runtime as runtime
        alive = runtime._worker_ready and runtime._worker_thread is not None and runtime._worker_thread.is_alive()
        return {"ok": alive, "ready": runtime._worker_ready}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}


def _check_storage() -> dict[str, str | bool]:
    try:
        ObjectStorage().ensure_bucket()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:200]}


def _check_download_work_dir() -> dict[str, str | bool]:
    try:
        work_dir = Path(get_settings().download_work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        probe = work_dir / f".ready-{uuid4().hex}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return {"ok": True, "path": str(work_dir)}
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
