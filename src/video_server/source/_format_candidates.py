"""Build normalized candidates from raw extractor formats."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import rfc8785

from video_server.errors import DomainError
from video_server.source._format_types import (
    NormalizedFormat,
    codec,
    compatible,
    identifier,
    integer,
    number,
    text,
)


def _signal_enabled(value: Any) -> bool:
    if value is None or value is False or value == 0:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "none", "false", "no", "clear", "unencrypted"}
    if isinstance(value, list | tuple | set | frozenset | dict):
        return bool(value)
    return True


def _reject_drm(raw_formats: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "_has_drm",
        "has_drm",
        "is_drm",
        "drm",
        "drm_family",
        "drm_families",
        "is_encrypted",
        "encrypted",
        "encryption",
        "key_system",
        "license_url",
    )
    field_signal = any(_signal_enabled(raw.get(field)) for raw in raw_formats for field in fields)
    note_signal = any("drm" in (text(raw.get("format_note")) or "") for raw in raw_formats)
    if field_signal or note_signal:
        raise DomainError("SOURCE_DRM_UNSUPPORTED", "DRM-protected formats are not supported")


def _is_discarded(raw: Mapping[str, Any]) -> bool:
    note = " ".join(filter(None, (text(raw.get("format_note")), text(raw.get("format")))))
    return bool(
        raw.get("is_live")
        or text(raw.get("live_status")) in {"is_live", "is_upcoming"}
        or "storyboard" in note
        or text(raw.get("ext")) in {"jpg", "jpeg", "png", "gif", "webp"}
    )


def _component_size(raw: Mapping[str, Any]) -> tuple[int | None, bool]:
    exact = integer(raw.get("filesize"))
    if exact is not None:
        return exact, False
    approximate = integer(raw.get("filesize_approx"))
    if approximate is not None:
        return approximate, True
    duration = number(raw.get("duration"))
    bitrate = number(raw.get("tbr")) or number(raw.get("vbr")) or number(raw.get("abr"))
    if duration is None or bitrate is None:
        return None, False
    return int(duration * bitrate * 1000 / 8), True


def _select_audio(
    video: Mapping[str, Any], audios: Sequence[Mapping[str, Any]], locale: str
) -> Mapping[str, Any] | None:
    choices = [audio for audio in audios if compatible(video, audio)]
    if not choices:
        return None
    requested = locale.replace("_", "-").lower().split("-", 1)[0]

    def key(audio: Mapping[str, Any]) -> tuple[int, float, float, str, bytes]:
        language = (text(audio.get("language")) or "").replace("_", "-").split("-", 1)[0]
        preference = (
            0 if language == requested else 1 if not language else 2 if language == "en" else 3
        )
        return (
            preference,
            -(number(audio.get("abr")) or 0),
            -(number(audio.get("channels")) or 0),
            codec(audio.get("acodec")) or "",
            identifier(audio).encode(),
        )

    return min(choices, key=key)


def _label(
    height: int | None,
    fps: float | None,
    dynamic: str | None,
    ext: str | None,
    merge: bool,
) -> str:
    parts = ["原始" if height is None else f"{height}p"]
    if fps is not None and fps != 30:
        parts.append(f"{fps:g}fps")
    if dynamic is not None and dynamic != "SDR":
        parts.append(dynamic)
    if ext is not None:
        parts.append(ext.upper())
    if merge:
        parts.append("需合并")
    return " · ".join(parts)


def _make(video: Mapping[str, Any], audio: Mapping[str, Any] | None) -> NormalizedFormat:
    components = (video,) if audio is None else (video, audio)
    component_ids = tuple(identifier(item) for item in components)
    sizes = [_component_size(item) for item in components]
    has_all_sizes = all(size is not None for size, _ in sizes)
    estimated_bytes = sum(size for size, _ in sizes if size is not None) if has_all_sizes else None
    size_is_estimate = any(estimate for _, estimate in sizes) if has_all_sizes else False
    width, height = integer(video.get("width")), integer(video.get("height"))
    fps, container = number(video.get("fps")), text(video.get("ext"))
    dynamic = text(video.get("dynamic_range"))
    dynamic = dynamic.upper() if dynamic is not None else None
    video_codec = codec(video.get("vcodec"))
    audio_source = audio if audio is not None else video
    audio_codec = codec(audio_source.get("acodec"))
    merge = audio is not None
    fingerprint_data = {
        "audio_codec": audio_codec,
        "audio_format_id": component_ids[1] if merge else "",
        "container": container,
        "dynamic_range": dynamic,
        "estimated_bytes": estimated_bytes,
        "fps": fps,
        "has_audio": True,
        "has_video": True,
        "height": height,
        "requires_merge": merge,
        "size_is_estimate": size_is_estimate,
        "video_codec": video_codec,
        "video_format_id": component_ids[0],
        "width": width,
    }
    bitrate = sum(
        (number(item.get("tbr")) or number(item.get("vbr")) or number(item.get("abr")) or 0)
        for item in components
    )
    return NormalizedFormat(
        component_ids=component_ids,
        fingerprint_sha256=hashlib.sha256(rfc8785.dumps(fingerprint_data)).hexdigest(),
        label=_label(height, fps, dynamic, container, merge),
        width=width,
        height=height,
        fps=fps,
        dynamic_range=dynamic,
        container=container,
        video_codec=video_codec,
        audio_codec=audio_codec,
        estimated_bytes=estimated_bytes,
        size_is_estimate=size_is_estimate,
        recommended=False,
        total_bitrate=bitrate,
    )


def build_candidates(
    raw_formats: Sequence[Mapping[str, Any]], locale: str
) -> list[NormalizedFormat]:
    _reject_drm(raw_formats)
    usable = [raw for raw in raw_formats if not _is_discarded(raw)]
    audios = [
        raw for raw in usable if codec(raw.get("vcodec")) is None and codec(raw.get("acodec"))
    ]
    candidates: list[NormalizedFormat] = []
    for video in usable:
        if codec(video.get("vcodec")) is None or text(video.get("ext")) is None:
            continue
        audio = None if codec(video.get("acodec")) else _select_audio(video, audios, locale)
        if codec(video.get("acodec")) is None and audio is None:
            continue
        candidates.append(_make(video, audio))
    return candidates
