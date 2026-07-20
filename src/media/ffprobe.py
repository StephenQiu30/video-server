"""ffprobe invocation and final audio/video validation."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediaProbeError(RuntimeError):
    """Raised when ffprobe cannot prove a playable audio-video file."""


@dataclass(frozen=True, slots=True)
class ProbeResult:
    format_name: str
    duration_seconds: float | None
    streams: tuple[dict[str, Any], ...]

    @property
    def has_video(self) -> bool:
        return any(item.get("codec_type") == "video" for item in self.streams)

    @property
    def has_audio(self) -> bool:
        return any(item.get("codec_type") == "audio" for item in self.streams)


def build_ffprobe_args(path: Path, *, binary: str = "ffprobe") -> list[str]:
    return [
        binary,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]


def probe_media(
    path: Path,
    *,
    timeout_seconds: int = 60,
    binary: str = "ffprobe",
) -> ProbeResult:
    """Run ffprobe with an argument list and require both media streams."""

    try:
        completed = subprocess.run(
            build_ffprobe_args(path, binary=binary),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MediaProbeError("ffprobe could not inspect the output") from exc
    if completed.returncode != 0:
        raise MediaProbeError("ffprobe rejected the output")
    try:
        payload = json.loads(completed.stdout)
        raw_streams = payload.get("streams", [])
        raw_format = payload.get("format", {})
        streams = tuple(item for item in raw_streams if isinstance(item, dict))
        duration = raw_format.get("duration")
        duration_value = float(duration) if duration is not None else None
        result = ProbeResult(
            format_name=str(raw_format.get("format_name") or "unknown"),
            duration_seconds=duration_value,
            streams=streams,
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MediaProbeError("ffprobe returned invalid JSON") from exc
    if not result.has_video or not result.has_audio:
        raise MediaProbeError("output must contain both video and audio streams")
    return result


__all__ = ["MediaProbeError", "ProbeResult", "build_ffprobe_args", "probe_media"]
