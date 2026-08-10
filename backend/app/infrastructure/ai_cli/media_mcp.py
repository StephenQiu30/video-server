from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any


class VideoObserver:
    def __init__(self, arguments: Any) -> None:
        self.root = Path(arguments.workspace).resolve(strict=True)
        self.video = (self.root / "input" / "video.bin").resolve(strict=True)
        if not self.video.is_relative_to(self.root):
            raise ValueError("invalid video workspace")
        self.ffmpeg = Path(arguments.ffmpeg).resolve(strict=True)
        self.ffprobe = Path(arguments.ffprobe).resolve(strict=True)
        self.duration_ms = arguments.duration_ms
        self.maximum_images = arguments.maximum_images
        self.maximum_image_bytes = arguments.maximum_image_bytes
        self.generated = 0

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "probe_video":
                return self._probe()
            if name == "inspect_video_overview":
                return self._overview(arguments)
            if name == "inspect_video_frame":
                return self._frame(arguments)
            raise ValueError("unknown video observation tool")
        except (OSError, ValueError, subprocess.SubprocessError):
            return _error("Video observation failed for the requested interval.")

    def _probe(self) -> dict[str, Any]:
        result = self._run(
            self.ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name:stream=codec_type,width,height,r_frame_rate",
            "-of",
            "json",
            str(self.video),
        )
        return _text(result.stdout.decode("utf-8", errors="replace"))

    def _overview(self, arguments: dict[str, Any]) -> dict[str, Any]:
        start, end = self._interval(arguments)
        path = self._next_path("contact-sheets")
        rate = f"16000/{end - start}"
        video_filter = (
            f"fps={rate},scale=320:180:force_original_aspect_ratio=decrease,"
            "pad=320:180:(ow-iw)/2:(oh-ih)/2,"
            "tile=layout=4x4:nb_frames=16:padding=2:margin=2"
        )
        self._run(
            self.ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start / 1000:.3f}",
            "-i",
            str(self.video),
            "-t",
            f"{(end - start) / 1000:.3f}",
            "-an",
            "-vf",
            video_filter,
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(path),
        )
        timestamps = [round(start + index * (end - start) / 16) for index in range(16)]
        return self._image(path, f"Cells left-to-right, top-to-bottom: {timestamps} ms")

    def _frame(self, arguments: dict[str, Any]) -> dict[str, Any]:
        timestamp = _integer(arguments, "timestamp_ms")
        if timestamp < 0 or timestamp >= self.duration_ms:
            raise ValueError("timestamp outside video")
        path = self._next_path("frames")
        self._run(
            self.ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp / 1000:.3f}",
            "-i",
            str(self.video),
            "-an",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(path),
        )
        return self._image(path, f"Frame near {timestamp} ms")

    def _interval(self, arguments: dict[str, Any]) -> tuple[int, int]:
        start = _integer(arguments, "start_ms")
        end = _integer(arguments, "end_ms")
        if start < 0 or end <= start or end > self.duration_ms:
            raise ValueError("interval outside video")
        return start, end

    def _next_path(self, directory: str) -> Path:
        if self.generated >= self.maximum_images:
            raise ValueError("image limit reached")
        self.generated += 1
        target = self.root / "work" / directory
        target.mkdir(parents=True, exist_ok=True)
        return target / f"agent-observation-{self.generated:03d}.jpg"

    def _image(self, path: Path, text: str) -> dict[str, Any]:
        data = path.read_bytes()
        if not data or len(data) > self.maximum_image_bytes:
            raise ValueError("invalid observation image")
        return {
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image",
                    "data": base64.b64encode(data).decode(),
                    "mimeType": "image/jpeg",
                },
            ]
        }

    def _run(
        self, executable: Path, *arguments: str
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            (str(executable), *arguments),
            cwd=self.root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
            check=True,
            creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)),
        )


def _integer(arguments: dict[str, Any], name: str) -> int:
    value = arguments.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("invalid integer argument")
    return value


def _text(value: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": value}]}


def _error(value: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": value}], "isError": True}
