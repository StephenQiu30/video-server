from datetime import UTC, datetime, timedelta
from pathlib import Path
import shutil
import subprocess

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import DownloadTask
from app.services.storage import ObjectStorage
from app.services.tasks import add_task_event
from app.utils.sanitize import redact_url, safe_filename
from video_downloader_shared.states import TaskState


def process_download_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = db.get(DownloadTask, task_id)
        if not task:
            return
        if task.state == TaskState.CANCELED.value:
            return
        _mark_running(db, task)
        _assert_media_tools_available()
        output_path = _download(task, db)
        _assert_size(output_path)
        _probe_with_ffprobe(output_path, db, task)
        object_key = _upload(task, output_path)
        task.state = TaskState.SUCCEEDED.value
        task.progress = 100
        task.output_filename = output_path.name
        task.object_key = object_key
        task.object_size = output_path.stat().st_size
        task.expires_at = datetime.now(UTC) + timedelta(hours=get_settings().file_retention_hours)
        add_task_event(db, task, TaskState.SUCCEEDED, "文件已保存到私有对象存储")
        db.commit()
    except Exception as exc:
        _mark_failed(db, task_id, exc)
        raise
    finally:
        db.close()


def _mark_running(db: Session, task: DownloadTask) -> None:
    task.state = TaskState.RUNNING.value
    task.progress = 5
    add_task_event(db, task, TaskState.RUNNING, "Worker 已开始下载")
    db.commit()


def _download(task: DownloadTask, db: Session) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise RuntimeError("下载内核未安装") from exc

    settings = get_settings()
    task_dir = Path(settings.download_dir) / f"user-{task.user_id}" / task.id
    task_dir.mkdir(parents=True, exist_ok=True)
    title = safe_filename(task.title or task.id)
    output_template = str(task_dir / f"{title}.%(ext)s")

    def progress_hook(payload: dict) -> None:
        if payload.get("status") != "downloading":
            return
        total = payload.get("total_bytes") or payload.get("total_bytes_estimate")
        downloaded = payload.get("downloaded_bytes") or 0
        if total:
            task.progress = max(5, min(95, int(downloaded / total * 90)))
            db.commit()

    requested_format = task.format_id or "best"
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("当前环境缺少 FFmpeg，无法执行下载任务")

    options = {
        "format": requested_format,
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "max_filesize": settings.max_file_size_bytes,
        "socket_timeout": 30,
    }
    options["ffmpeg_location"] = ffmpeg_path
    options["merge_output_format"] = "mp4"
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info(task.source_url, download=True)
        filename = ydl.prepare_filename(result)
    return _resolve_output_path(task_dir, Path(filename))


def _resolve_output_path(task_dir: Path, prepared_path: Path) -> Path:
    if prepared_path.exists():
        return prepared_path
    files = [path for path in task_dir.iterdir() if path.is_file()]
    if not files:
        raise RuntimeError("下载完成后未找到输出文件")
    return max(files, key=lambda path: path.stat().st_mtime)


def _assert_size(path: Path) -> None:
    max_size = get_settings().max_file_size_bytes
    size = path.stat().st_size
    if size > max_size:
        raise RuntimeError(f"文件超过限制：{size} > {max_size}")


def _probe_with_ffprobe(path: Path, db: Session, task: DownloadTask) -> None:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise RuntimeError("当前环境缺少 ffprobe，无法校验输出文件")
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("FFmpeg / ffprobe 无法校验输出文件")


def _assert_media_tools_available() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"当前环境缺少媒体工具：{', '.join(missing)}")


def _upload(task: DownloadTask, output_path: Path) -> str:
    object_key = f"users/{task.user_id}/tasks/{task.id}/{output_path.name}"
    ObjectStorage().upload_file(str(output_path), object_key)
    return object_key


def _mark_failed(db: Session, task_id: str, exc: Exception) -> None:
    task = db.get(DownloadTask, task_id)
    if not task or task.state == TaskState.CANCELED.value:
        return
    reason = _format_failure_reason(exc)
    task.state = TaskState.FAILED.value
    task.failure_code = "download_failed"
    task.failure_reason = reason
    add_task_event(db, task, TaskState.FAILED, task.failure_reason)
    db.commit()


def _format_failure_reason(exc: Exception) -> str:
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else "下载任务失败"
    if message.startswith("ERROR: "):
        message = message[len("ERROR: ") :]
    return redact_url(message)[:300]


def cleanup_expired_outputs() -> int:
    db = SessionLocal()
    removed = 0
    try:
        now = datetime.now(UTC)
        tasks = db.scalars(
            select(DownloadTask).where(
                DownloadTask.state == TaskState.SUCCEEDED.value,
                DownloadTask.object_key.is_not(None),
                DownloadTask.expires_at.is_not(None),
                DownloadTask.expires_at <= now,
            )
        )
        storage = ObjectStorage()
        for task in tasks:
            try:
                storage.delete_object(task.object_key)
            except Exception:
                pass
            task.object_key = None
            task.failure_code = "retention_expired"
            task.failure_reason = "文件保留时间已过期并已清理"
            add_task_event(db, task, task.state, "过期文件已清理")
            removed += 1
        db.commit()
        return removed
    finally:
        db.close()
