from pathlib import Path
import shutil
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DownloadTask
from app.services.tasks import add_task_event
from app.utils.sanitize import safe_filename
from video_downloader_shared.states import TaskState
from worker.domain import DownloadArtifact
from worker.failures import JobFailure, raise_task_canceled


def download_task_artifact(
    task: DownloadTask,
    db: Session,
    task_dir: Path,
    is_canceled: Callable[[Session, DownloadTask], bool],
) -> tuple[DownloadArtifact, dict]:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise JobFailure("download_failed", "下载内核未安装") from exc

    settings = get_settings()
    task_dir.mkdir(parents=True, exist_ok=True)
    title = safe_filename(task.title or task.id)
    output_template = str(task_dir / f"{title}.%(ext)s")

    def progress_hook(payload: dict) -> None:
        if is_canceled(db, task):
            raise_task_canceled()
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
    apply_download_resilience_options(options)
    apply_browser_cookie_options(options, settings.ytdlp_cookies_from_browser)
    options["ffmpeg_location"] = ffmpeg_path
    options["merge_output_format"] = "mp4"
    with YoutubeDL(options) as ydl:
        result = ydl.extract_info(task.source_url, download=True)
        filename = ydl.prepare_filename(result)
    output_path = resolve_output_path(task_dir, Path(filename))
    add_task_event(db, task, TaskState.RUNNING, "源文件下载完成")
    db.commit()
    artifact = DownloadArtifact(path=output_path, filename=output_path.name, size_bytes=output_path.stat().st_size)
    return artifact, result


def apply_browser_cookie_options(options: dict, browser_name: str | None) -> None:
    browser = (browser_name or "").strip().lower()
    if not browser or browser in {"none", "false", "off"}:
        return
    if browser not in {"chrome", "chromium", "edge", "firefox", "safari"}:
        raise JobFailure("browser_cookies_unavailable", "浏览器登录态配置无效，请检查 YTDLP_COOKIES_FROM_BROWSER")
    options["cookiesfrombrowser"] = (browser,)


def apply_download_resilience_options(options: dict) -> None:
    options.update(
        {
            "retries": 3,
            "fragment_retries": 3,
            "file_access_retries": 3,
            "continuedl": True,
        }
    )


def resolve_output_path(task_dir: Path, prepared_path: Path) -> Path:
    if prepared_path.exists():
        return prepared_path
    files = [path for path in task_dir.iterdir() if path.is_file()]
    if not files:
        raise JobFailure("download_failed", "下载完成后未找到输出文件")
    return max(files, key=lambda path: path.stat().st_mtime)
