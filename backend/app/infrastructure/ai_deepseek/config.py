from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeepSeekAdapterConfig:
    model: str
    base_url: str
    ffmpeg: Path
    ffprobe: Path
    timeout_seconds: float
    max_stdout_bytes: int
    max_stderr_bytes: int
    max_workspace_bytes: int
    max_workspace_files: int
    max_frames: int
    max_image_bytes: int
    workspace_poll_seconds: float
    terminate_grace_seconds: float

    def __post_init__(self) -> None:
        limits = (
            self.timeout_seconds,
            self.max_stdout_bytes,
            self.max_stderr_bytes,
            self.max_workspace_bytes,
            self.max_workspace_files,
            self.max_frames,
            self.max_image_bytes,
            self.workspace_poll_seconds,
            self.terminate_grace_seconds,
        )
        if (
            not self.model.strip()
            or not self.base_url.startswith(("http://", "https://"))
            or not self.ffmpeg.is_absolute()
            or not self.ffprobe.is_absolute()
            or any(isinstance(value, bool) or value <= 0 for value in limits)
        ):
            raise ValueError("DeepSeek adapter configuration is invalid")
