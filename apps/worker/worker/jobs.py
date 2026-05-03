from datetime import UTC, datetime, timedelta
from pathlib import Path
import shutil
import subprocess
from typing import NoReturn

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import DownloadTask
from app.services.storage import ObjectStorage
from app.services.tasks import add_task_event, cleanup_expired_task_outputs
from app.utils.sanitize import redact_url, safe_filename
from video_downloader_shared.states import TaskState


class JobFailure(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def process_download_task(task_id: str) -> None:
    db = SessionLocal()
    task_work_dir: Path | None = None
    try:
        task = db.get(DownloadTask, task_id)
        if not task:
            return
        if task.state == TaskState.CANCELED.value:
            return
        _mark_running(db, task)
        _assert_media_tools_available()
        task_work_dir = _task_work_dir(task)
        output_path = _download(task, db, task_work_dir)
        if _is_canceled(db, task):
            return
        _assert_size(output_path, task)
        add_task_event(db, task, TaskState.RUNNING, "开始校验媒体文件")
        db.commit()
        _probe_with_ffprobe(output_path, db, task)
        if _is_canceled(db, task):
            return
        add_task_event(db, task, TaskState.RUNNING, "开始上传到私有对象存储")
        db.commit()
        object_key = _upload(task, output_path)
        if _is_canceled(db, task):
            ObjectStorage().delete_object(object_key)
            return
        task.state = TaskState.SUCCEEDED.value
        task.progress = 100
        task.output_filename = output_path.name
        task.object_key = object_key
        task.object_size = output_path.stat().st_size
        task.expires_at = datetime.now(UTC) + timedelta(hours=task.user.file_retention_hours)
        add_task_event(db, task, TaskState.SUCCEEDED, "文件已保存到私有对象存储")
        db.commit()
    except Exception as exc:
        _mark_failed(db, task_id, exc)
        raise
    finally:
        _cleanup_task_work_dir(task_work_dir)
        db.close()


def _mark_running(db: Session, task: DownloadTask) -> None:
    task.state = TaskState.RUNNING.value
    task.progress = 5
    add_task_event(db, task, TaskState.RUNNING, "Worker 已开始下载")
    db.commit()


def _is_canceled(db: Session, task: DownloadTask) -> bool:
    db.refresh(task)
    return task.state == TaskState.CANCELED.value


def _task_work_dir(task: DownloadTask) -> Path:
    settings = get_settings()
    return Path(settings.download_work_dir) / f"user-{task.user_id}" / task.id


def _download(task: DownloadTask, db: Session, task_dir: Path) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise JobFailure("download_failed", "下载内核未安装") from exc

    settings = get_settings()
    task_dir.mkdir(parents=True, exist_ok=True)
    title = safe_filename(task.title or task.id)
    output_template = str(task_dir / f"{title}.%(ext)s")

    def progress_hook(payload: dict) -> None:
        if _is_canceled(db, task):
            _raise_task_canceled()
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
        raise JobFailure("media_tools_missing", "当前环境缺少 FFmpeg，无法执行下载任务")

    add_task_event(db, task, TaskState.RUNNING, "开始下载源文件")
    db.commit()
    options = {
        "format": requested_format,
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "max_filesize": min(settings.max_file_size_bytes, task.user.max_file_size_bytes),
        "socket_timeout": 30,
    }
    _apply_download_resilience_options(options)
    _apply_browser_cookie_options(options, settings.ytdlp_cookies_from_browser)
    options["ffmpeg_location"] = ffmpeg_path
    options["merge_output_format"] = "mp4"
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info(task.source_url, download=True)
        filename = ydl.prepare_filename(result)
    output_path = _resolve_output_path(task_dir, Path(filename))
    add_task_event(db, task, TaskState.RUNNING, "源文件下载完成")
    db.commit()
    return output_path


def _raise_task_canceled() -> NoReturn:
    raise JobFailure("task_canceled", "任务已取消")


def _apply_browser_cookie_options(options: dict, browser_name: str | None) -> None:
    browser = (browser_name or "").strip().lower()
    if not browser or browser in {"none", "false", "off"}:
        return
    if browser not in {"chrome", "chromium", "edge", "firefox", "safari"}:
        raise JobFailure("browser_cookies_unavailable", "浏览器登录态配置无效，请检查 YTDLP_COOKIES_FROM_BROWSER")
    options["cookiesfrombrowser"] = (browser,)


def _apply_download_resilience_options(options: dict) -> None:
    options.update(
        {
            "retries": 3,
            "fragment_retries": 3,
            "file_access_retries": 3,
            "continuedl": True,
        }
    )


def _resolve_output_path(task_dir: Path, prepared_path: Path) -> Path:
    if prepared_path.exists():
        return prepared_path
    files = [path for path in task_dir.iterdir() if path.is_file()]
    if not files:
        raise JobFailure("download_failed", "下载完成后未找到输出文件")
    return max(files, key=lambda path: path.stat().st_mtime)


def _cleanup_task_work_dir(task_dir: Path | None) -> None:
    if task_dir is not None:
        shutil.rmtree(task_dir, ignore_errors=True)


def _assert_size(path: Path, task: DownloadTask) -> None:
    max_size = min(get_settings().max_file_size_bytes, task.user.max_file_size_bytes)
    size = path.stat().st_size
    if size > max_size:
        raise JobFailure("file_too_large", f"文件超过限制：{size} > {max_size}")


def _probe_with_ffprobe(path: Path, db: Session, task: DownloadTask) -> None:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise JobFailure("media_tools_missing", "当前环境缺少 ffprobe，无法校验输出文件")
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise JobFailure("ffprobe_failed", "FFmpeg / ffprobe 无法校验输出文件")


def _assert_media_tools_available() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise JobFailure("media_tools_missing", f"当前环境缺少媒体工具：{', '.join(missing)}")


def _upload(task: DownloadTask, output_path: Path) -> str:
    object_key = f"users/{task.user_id}/tasks/{task.id}/{output_path.name}"
    try:
        ObjectStorage().upload_file(str(output_path), object_key)
    except Exception as exc:
        raise JobFailure("storage_failed", "文件上传对象存储失败") from exc
    return object_key


def _mark_failed(db: Session, task_id: str, exc: Exception) -> None:
    task = db.get(DownloadTask, task_id)
    if not task or task.state == TaskState.CANCELED.value:
        return
    reason = _format_failure_reason(exc)
    task.state = TaskState.FAILED.value
    task.failure_code = _failure_code(exc)
    task.failure_reason = reason
    add_task_event(db, task, TaskState.FAILED, task.failure_reason)
    db.commit()


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, JobFailure):
        return exc.code
    message = str(exc).lower()
    if "requested format is not available" in message or "format is not available" in message:
        return "format_unavailable"
    if "file is larger than max-filesize" in message or "larger than max-filesize" in message:
        return "file_too_large"
    if "timed out" in message or "timeout" in message:
        return "task_timeout"
    if _looks_like_browser_cookie_error(message):
        return "browser_cookies_unavailable"
    return "download_failed"


def _format_failure_reason(exc: Exception) -> str:
    if isinstance(exc, JobFailure) and exc.code == "task_canceled":
        return "任务已取消"
    if _looks_like_browser_cookie_error(str(exc).lower()):
        return (
            "无法读取本机 Chrome 登录态。请确认 Chrome 已登录 B 站，并允许当前终端或 Python 访问浏览器数据；"
            "如果只下载公开视频，也可以关闭 YTDLP_COOKIES_FROM_BROWSER 后重试。"
        )
    lowered_message = str(exc).lower()
    if "requested format is not available" in lowered_message or "format is not available" in lowered_message:
        return "该视频源未提供所选清晰度，请选择推荐下载或其他可用清晰度后重试。"
    if "unsupported url" in lowered_message or "no video formats found" in lowered_message:
        return "该公开视频暂不支持解析或平台规则已变化，请换用公开视频链接后重试。"
    message = str(exc).strip().splitlines()[0] if str(exc).strip() else "下载任务失败"
    if message.startswith("ERROR: "):
        message = message[len("ERROR: ") :]
    return redact_url(message)[:300]


def _looks_like_browser_cookie_error(message: str) -> bool:
    needles = (
        "cookies",
        "cookie",
        "cookiesfrombrowser",
        "keyring",
        "keychain",
        "browser",
        "chrome",
        "chromium",
    )
    return any(needle in message for needle in needles)


def cleanup_expired_outputs() -> int:
    db = SessionLocal()
    try:
        return cleanup_expired_task_outputs(db)
    finally:
        db.close()
