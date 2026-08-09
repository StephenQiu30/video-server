from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CliAdapterConfig:
    binary: Path
    model: str
    ffmpeg: Path
    ffprobe: Path
    timeout_seconds: float = 900
    max_stdout_bytes: int = 2 * 1024 * 1024
    max_stderr_bytes: int = 128 * 1024
    max_workspace_bytes: int = 4 * 1024**3
    max_workspace_files: int = 512
    max_frames: int = 256
    max_image_bytes: int = 20 * 1024**2
    workspace_poll_seconds: float = 0.25
    terminate_grace_seconds: float = 2
    max_turns: int = 40

    def __post_init__(self) -> None:
        paths = (self.binary, self.ffmpeg, self.ffprobe)
        if any(not path.is_absolute() for path in paths) or not self.model.strip():
            raise ValueError("CLI binaries must be absolute and model cannot be blank")
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
            self.max_turns,
        )
        if any(isinstance(value, bool) or value <= 0 for value in limits):
            raise ValueError("CLI adapter limits must be positive")
