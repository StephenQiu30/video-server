"""Safe FFmpeg stream-copy merge helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


class MediaMergeError(RuntimeError):
    """Raised when FFmpeg cannot remux separated streams."""


def build_merge_args(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    *,
    binary: str = "ffmpeg",
) -> list[str]:
    """Build a shell-free remux command; no user selector is interpolated."""

    return [
        binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c",
        "copy",
        str(output_path),
    ]


def merge_streams(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    *,
    timeout_seconds: int = 1800,
    binary: str = "ffmpeg",
) -> Path:
    try:
        completed = subprocess.run(
            build_merge_args(video_path, audio_path, output_path, binary=binary),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MediaMergeError("ffmpeg merge timed out or was unavailable") from exc
    if completed.returncode != 0 or not output_path.is_file():
        raise MediaMergeError("ffmpeg could not merge the media streams")
    return output_path


__all__ = ["MediaMergeError", "build_merge_args", "merge_streams"]
