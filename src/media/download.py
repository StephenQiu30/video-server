"""Constrained yt-dlp download and final artifact preparation."""

from __future__ import annotations

import re
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.media.ffprobe import ProbeResult, probe_media
from src.media.formats import NormalizedFormat
from src.media.sha256 import sha256_file
from src.media.url_policy import URLPolicy, UrlPolicyError


class MediaDownloadError(RuntimeError):
    """Base error for deterministic download failures."""


class MediaSizeLimitError(MediaDownloadError):
    """The downloaded file exceeds the configured byte limit."""


@dataclass(frozen=True, slots=True)
class DownloadLimits:
    timeout_seconds: int = 1800
    max_size_bytes: int = 2 * 1024**3
    max_duration_seconds: int = 7200
    temp_dir: Path = Path("/tmp/video-downloads")


@dataclass(frozen=True, slots=True)
class DownloadedMedia:
    path: Path
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    probe: ProbeResult


def sanitize_filename(title: str, *, extension: str = "mp4") -> str:
    """Turn untrusted media titles into a safe, bounded basename."""

    cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", str(title or ""))
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = re.sub(r"[<>:\"|?*]", "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = cleaned[:180] or "video"
    ext = re.sub(r"[^a-z0-9]+", "", extension.lower()) or "mp4"
    return f"{cleaned}.{ext}"


def content_type_for(extension: str) -> str:
    return {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "mov": "video/quicktime",
    }.get(extension.lower().lstrip("."), "application/octet-stream")


@contextmanager
def job_workspace(job_id: uuid.UUID | str, *, root: Path) -> Iterator[Path]:
    """Create and always remove one isolated job directory."""

    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{job_id}-", dir=str(root)) as path:
        yield Path(path)


class MediaDownloader:
    """Run only server-generated selectors through yt-dlp's Python API."""

    def __init__(
        self,
        *,
        limits: DownloadLimits | None = None,
        policy: URLPolicy | None = None,
        ytdlp_class: type[Any] | None = None,
        ffprobe_binary: str = "ffprobe",
    ) -> None:
        self.limits = limits or DownloadLimits()
        self.policy = policy or URLPolicy()
        self._ytdlp_class = ytdlp_class
        self.ffprobe_binary = ffprobe_binary

    def _client_class(self) -> type[Any]:
        if self._ytdlp_class is not None:
            return self._ytdlp_class
        try:
            from yt_dlp import YoutubeDL  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise MediaDownloadError("yt-dlp dependency is unavailable") from exc
        return YoutubeDL  # type: ignore[no-any-return]

    def _options(
        self, *, source_url: str, format_option: NormalizedFormat, workspace: Path
    ) -> dict[str, Any]:
        # The selector is assembled from provider IDs stored by our database;
        # no HTTP request may pass a raw selector into this function.
        return {
            "ignoreconfig": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "format": format_option.selector,
            "outtmpl": str(workspace / "download.%(ext)s"),
            "merge_output_format": format_option.container,
            "socket_timeout": min(self.limits.timeout_seconds, 300),
            "retries": 0,
            "fragment_retries": 0,
            "continuedl": False,
            "overwrites": True,
            "nopart": False,
        }

    def _progress_hook(self, status: dict[str, Any]) -> None:
        downloaded = status.get("downloaded_bytes")
        if downloaded is not None and int(downloaded) > self.limits.max_size_bytes:
            raise MediaSizeLimitError("download exceeds the configured size limit")

    def _download_files(
        self, source_url: str, format_option: NormalizedFormat, workspace: Path
    ) -> list[Path]:
        try:
            validated = self.policy.validate(source_url)
        except UrlPolicyError as exc:
            raise MediaDownloadError(str(exc)) from exc
        options = self._options(
            source_url=validated.value,
            format_option=format_option,
            workspace=workspace,
        )
        options["progress_hooks"] = [self._progress_hook]
        try:
            with self._client_class()(options) as client:
                client.download([validated.value])
        except MediaSizeLimitError:
            raise
        except Exception as exc:
            raise MediaDownloadError("media download failed") from exc
        files = [
            item
            for item in workspace.iterdir()
            if item.is_file()
            and not item.name.endswith((".part", ".ytdl"))
            and item.stat().st_size > 0
        ]
        if not files:
            raise MediaDownloadError("yt-dlp produced no media file")
        return sorted(files, key=lambda item: item.stat().st_size, reverse=True)

    def download_to_workspace(
        self,
        *,
        source_url: str,
        format_option: NormalizedFormat,
        title: str,
        workspace: Path,
    ) -> DownloadedMedia:
        workspace.mkdir(parents=True, exist_ok=True)
        files = self._download_files(source_url, format_option, workspace)
        output = files[0]
        size = output.stat().st_size
        if size > self.limits.max_size_bytes:
            raise MediaSizeLimitError("download exceeds the configured size limit")
        try:
            probe = probe_media(
                output,
                timeout_seconds=min(self.limits.timeout_seconds, 300),
                binary=self.ffprobe_binary,
            )
        except Exception as exc:
            raise MediaDownloadError("downloaded media failed validation") from exc
        if (
            probe.duration_seconds is not None
            and probe.duration_seconds > self.limits.max_duration_seconds
        ):
            raise MediaSizeLimitError("media duration exceeds the configured limit")
        extension = format_option.container or output.suffix.lstrip(".") or "mp4"
        final_name = sanitize_filename(title, extension=extension)
        # Constructing the path explicitly keeps the basename independent from
        # untrusted title text.
        safe_extension = re.sub(r"[^a-z0-9]+", "", extension.lower()) or "mp4"
        final_path = workspace / f"artifact.{safe_extension}"
        if output != final_path:
            output.replace(final_path)
            output = final_path
        size = output.stat().st_size
        return DownloadedMedia(
            path=output,
            file_name=final_name,
            content_type=content_type_for(extension),
            size_bytes=size,
            sha256=sha256_file(output),
            probe=probe,
        )


__all__ = [
    "DownloadLimits",
    "DownloadedMedia",
    "MediaDownloadError",
    "MediaDownloader",
    "MediaSizeLimitError",
    "content_type_for",
    "job_workspace",
    "sanitize_filename",
]
