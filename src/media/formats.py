"""Normalize yt-dlp format dictionaries into safe resolution options."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


class FormatPolicyError(ValueError):
    """Raised when yt-dlp returned an unusable format set."""


@dataclass(frozen=True, slots=True)
class NormalizedFormat:
    """A server-owned format option.

    ``video_format_id`` and ``audio_format_id`` are provider identifiers and
    must remain internal.  API schemas should expose only the generated
    database UUID and the display fields represented here.
    """

    video_format_id: str
    audio_format_id: str | None
    label: str
    width: int | None
    height: int | None
    fps: float | None
    container: str
    video_codec: str
    audio_codec: str
    estimated_size_bytes: int | None
    requires_merge: bool
    sort_order: int = 0

    @property
    def selector(self) -> str:
        if self.requires_merge and self.audio_format_id:
            return f"{self.video_format_id}+{self.audio_format_id}"
        return self.video_format_id

    def to_model_values(self) -> dict[str, object]:
        """Return fields accepted by ``MediaFormat`` without provider leaks."""

        return asdict(self)


def _text(value: object, default: str = "unknown") -> str:
    if value is None:
        return default
    result = str(value).strip()
    return result or default


def _positive_int(value: object) -> int | None:
    try:
        number = int(str(value)) if value is not None else 0
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _positive_float(value: object) -> float | None:
    try:
        number = float(str(value)) if value is not None else 0.0
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _size(item: Mapping[str, Any]) -> int | None:
    # ``filesize`` is exact; ``filesize_approx`` is still useful as a display
    # estimate but is never treated as a success/limit condition by itself.
    return _positive_int(item.get("filesize") or item.get("filesize_approx"))


def _has_video(item: Mapping[str, Any]) -> bool:
    return _text(item.get("vcodec"), "none").lower() not in {"none", ""}


def _has_audio(item: Mapping[str, Any]) -> bool:
    return _text(item.get("acodec"), "none").lower() not in {"none", ""}


def _score_single(item: Mapping[str, Any]) -> tuple[object, ...]:
    # Higher tuple values win.  Prefer a playable AV file, then common
    # container/codecs, known size and bitrate for deterministic ties.
    ext = _text(item.get("ext"), "unknown").lower()
    vcodec = _text(item.get("vcodec"), "unknown").lower()
    acodec = _text(item.get("acodec"), "unknown").lower()
    return (
        int(_has_audio(item)),
        int(ext in {"mp4", "webm", "mkv"}),
        int(vcodec in {"avc1", "h264", "av01", "vp9", "vp09"}),
        int(acodec in {"mp4a", "aac", "opus", "vorbis"}),
        int(_size(item) is not None),
        _positive_float(item.get("fps")) or 0.0,
        _positive_int(item.get("tbr")) or 0,
        _text(item.get("format_id")),
    )


def _score_audio(item: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        int(_text(item.get("acodec"), "none").lower() not in {"none", ""}),
        int(_text(item.get("ext"), "").lower() in {"m4a", "mp4", "webm", "opus"}),
        _positive_int(item.get("abr")) or 0,
        _positive_int(item.get("asr")) or 0,
        _text(item.get("format_id")),
    )


def _candidate_key(item: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        _positive_int(item.get("height")) or 0,
        _positive_int(item.get("width")) or 0,
        _text(item.get("format_id")),
    )


def normalize_formats(info: Mapping[str, Any]) -> list[NormalizedFormat]:
    """Return one playable option per video height, highest first.

    Generic/audio-only/storyboard formats are discarded.  When no AV format
    exists for a height, the best compatible audio-only stream is paired with
    that height and marked ``requires_merge``.
    """

    raw_formats = info.get("formats")
    if not isinstance(raw_formats, list):
        raise FormatPolicyError("extractor returned no formats")
    usable = [item for item in raw_formats if isinstance(item, Mapping)]
    videos = [
        item
        for item in usable
        if _has_video(item) and not bool(item.get("is_storyboard"))
    ]
    audios = [item for item in usable if _has_audio(item) and not _has_video(item)]
    if not videos:
        raise FormatPolicyError("extractor returned no video formats")
    best_audio = max(audios, key=_score_audio) if audios else None

    by_height: dict[int, list[Mapping[str, Any]]] = {}
    for item in videos:
        height = _positive_int(item.get("height"))
        if height is None:
            continue
        by_height.setdefault(height, []).append(item)
    result: list[NormalizedFormat] = []
    for height in sorted(by_height, reverse=True):
        candidates = by_height[height]
        single = [item for item in candidates if _has_audio(item)]
        chosen = max(single or candidates, key=_score_single)
        requires_merge = not _has_audio(chosen)
        if requires_merge and best_audio is None:
            # A video-only-only response cannot satisfy the MVP audio contract.
            continue
        width = _positive_int(chosen.get("width"))
        ext = _text(chosen.get("ext"), "mp4").lower()
        audio = chosen if _has_audio(chosen) else best_audio
        size = _size(chosen)
        if requires_merge and audio is not None:
            audio_size = _size(audio)
            if size is not None and audio_size is not None:
                size += audio_size
        result.append(
            NormalizedFormat(
                video_format_id=_text(chosen.get("format_id"), "unknown"),
                audio_format_id=(
                    _text(audio.get("format_id"), "unknown")
                    if requires_merge and audio is not None
                    else None
                ),
                label=f"{height}p",
                width=width,
                height=height,
                fps=_positive_float(chosen.get("fps")),
                container=ext,
                video_codec=_text(chosen.get("vcodec")),
                audio_codec=(
                    _text(audio.get("acodec")) if audio is not None else "unknown"
                ),
                estimated_size_bytes=size,
                requires_merge=requires_merge,
            )
        )
    if not result:
        raise FormatPolicyError("no playable audio-video format was returned")
    return [
        item.__class__(**{**asdict(item), "sort_order": index})
        for index, item in enumerate(result)
    ]


__all__ = ["FormatPolicyError", "NormalizedFormat", "normalize_formats"]
