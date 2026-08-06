from __future__ import annotations

from dataclasses import dataclass, fields

PROVIDER_UPLOAD_LIMIT_BYTES = 25_000_000


@dataclass(frozen=True, slots=True)
class AnalysisMediaSettings:
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    chunk_duration_ms: int = 600_000
    max_total_duration_ms: int = 21_600_000
    max_chunk_bytes: int = 24_000_000
    max_total_bytes: int = 750_000_000
    max_chunks: int = 64
    probe_timeout_seconds: float = 30.0
    extraction_timeout_seconds: float = 180.0
    output_capture_bytes: int = 64 * 1024
    terminate_grace_seconds: float = 1.0

    def __post_init__(self) -> None:
        for name in ("ffmpeg_bin", "ffprobe_bin"):
            value = getattr(self, name)
            if not value or "\x00" in value:
                raise ValueError(f"{name} must be a NUL-free executable")
        for item in fields(self):
            if item.name in {"ffmpeg_bin", "ffprobe_bin"}:
                continue
            value = getattr(self, item.name)
            if isinstance(value, bool) or value <= 0:
                raise ValueError(f"{item.name} must be positive")
        if self.max_chunk_bytes >= PROVIDER_UPLOAD_LIMIT_BYTES:
            raise ValueError("max_chunk_bytes must stay below the provider limit")
