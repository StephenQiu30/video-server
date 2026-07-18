"""Shared values for source-format normalization."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

_CODECS = (
    (("avc1", "h264"), "h264"),
    (("hev1", "hvc1", "hevc"), "hevc"),
    (("vp09", "vp9"), "vp9"),
    (("av01", "av1"), "av1"),
    (("mp4a", "aac"), "aac"),
    (("opus",), "opus"),
    (("vorbis",), "vorbis"),
)
MP4_VIDEO = frozenset({"mp4", "m4v", "mov"})
MP4_AUDIO = frozenset({"m4a", "aac"})
WEBM_VIDEO = frozenset({"webm"})
WEBM_AUDIO = frozenset({"webm", "weba", "opus", "vorbis"})


@dataclass(slots=True)
class NormalizedFormat:
    component_ids: tuple[str, ...]
    fingerprint_sha256: str
    label: str
    width: int | None
    height: int | None
    fps: float | None
    dynamic_range: str | None
    container: str | None
    video_codec: str | None
    audio_codec: str | None
    estimated_bytes: int | None
    size_is_estimate: bool
    recommended: bool
    total_bitrate: float

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "dynamic_range": self.dynamic_range,
            "container": self.container,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "has_audio": True,
            "has_video": True,
            "requires_merge": len(self.component_ids) == 2,
            "estimated_bytes": self.estimated_bytes,
            "size_is_estimate": self.size_is_estimate,
            "recommended": self.recommended,
        }


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def integer(value: Any) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None else None


def text(value: Any) -> str | None:
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def codec(value: Any) -> str | None:
    raw = text(value)
    if raw is None or raw in {"none", "null"}:
        return None
    for prefixes, normalized in _CODECS:
        if raw.startswith(prefixes):
            return normalized
    return f"other:{raw}"


def identifier(raw: Mapping[str, Any]) -> str:
    value = raw.get("format_id")
    return "" if value is None else str(value)


def family(ext: str | None) -> str | None:
    if ext in MP4_VIDEO:
        return "mp4"
    if ext in WEBM_VIDEO:
        return "webm"
    return None


def compatible(video: Mapping[str, Any], audio: Mapping[str, Any]) -> bool:
    video_ext, audio_ext = text(video.get("ext")), text(audio.get("ext"))
    return (video_ext in MP4_VIDEO and audio_ext in MP4_AUDIO) or (
        video_ext in WEBM_VIDEO and audio_ext in WEBM_AUDIO
    )
