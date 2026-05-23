from pathlib import Path
import shutil
import subprocess

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DownloadTask
from worker.domain import DownloadArtifact
from worker.failures import JobFailure


def assert_media_tools_available() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise JobFailure("media_tools_missing", f"当前环境缺少媒体工具：{', '.join(missing)}")


def assert_artifact_size(artifact: DownloadArtifact, task: DownloadTask) -> None:
    max_size = min(get_settings().max_file_size_bytes, task.user.max_file_size_bytes)
    if artifact.size_bytes > max_size:
        raise JobFailure("file_too_large", f"文件超过限制：{artifact.size_bytes} > {max_size}")


def probe_with_ffprobe(artifact: DownloadArtifact, db: Session, task: DownloadTask) -> None:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        raise JobFailure("media_tools_missing", "当前环境缺少 ffprobe，无法校验输出文件")
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(artifact.path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise JobFailure("ffprobe_failed", "FFmpeg / ffprobe 无法校验输出文件")


def artifact_from_path(path: Path) -> DownloadArtifact:
    return DownloadArtifact(path=path, filename=path.name, size_bytes=path.stat().st_size)
