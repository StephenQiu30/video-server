from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from app.domain.downloads import CandidateStream, DynamicRange, StreamKind
from app.runner.codecs import (
    audio_codec_family,
    container_family,
    video_codec_family,
)
from app.runner.errors import RunnerFailure
from app.runner.options import build_download_options
from app.runner.url_policy import UrlPolicyError, validate_media_url

__all__ = [
    "MediaInspection",
    "build_download_options",
    "enrich_direct_metadata",
    "enrich_format_metadata",
    "normalize_metadata",
    "normalize_selected_format_metadata",
]

_PROVIDER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


@dataclass(frozen=True, slots=True)
class MediaInspection:
    provider_media_id: str
    title: str
    duration_seconds: float
    extractor_key: str
    streams: tuple[CandidateStream, ...]
    thumbnail_url: str | None = None


def normalize_selected_format_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Represent yt-dlp's valid top-level selected format as one candidate.

    Single-representation extractors may omit ``formats`` from
    ``--dump-single-json`` while returning a selected ``format_id`` and media
    URL at the top level. Preserve that representation for the runner's common
    bounded-probe and semantic-format pipeline.
    """
    if isinstance(payload.get("formats"), list):
        return payload
    format_id = payload.get("format_id")
    url = payload.get("url")
    if not isinstance(format_id, str) or not isinstance(url, str):
        return payload
    selected = {
        key: value
        for key, value in payload.items()
        if key
        in {
            "abr",
            "acodec",
            "dynamic_range",
            "ext",
            "filesize",
            "filesize_approx",
            "format_id",
            "fps",
            "height",
            "language",
            "tbr",
            "url",
            "vbr",
            "vcodec",
            "width",
        }
    }
    normalized = dict(payload)
    normalized["formats"] = [selected]
    return normalized


def enrich_direct_metadata(
    payload: dict[str, Any], probe: dict[str, Any]
) -> dict[str, Any]:
    """Fill yt-dlp's sparse direct-file metadata from a proxy-bound ffprobe."""
    format_info = probe.get("format")
    probe_streams = probe.get("streams")
    raw_formats = payload.get("formats")
    if (
        not isinstance(format_info, dict)
        or not isinstance(probe_streams, list)
        or not isinstance(raw_formats, list)
    ):
        raise RunnerFailure("invalid_inspection_response", status=502)

    video = _first_probe_stream(probe_streams, "video")
    audio = _first_probe_stream(probe_streams, "audio")
    if video is None or audio is None:
        raise RunnerFailure("unsupported_source")
    duration = _positive_number(format_info.get("duration"))
    if duration is None:
        raise RunnerFailure("unsupported_source")

    enriched = dict(payload)
    enriched["duration"] = duration
    enriched_formats: list[object] = []
    for value in raw_formats:
        if not isinstance(value, dict):
            enriched_formats.append(value)
            continue
        raw = dict(value)
        raw.update(
            {
                "vcodec": video.get("codec_name"),
                "acodec": audio.get("codec_name"),
                "width": video.get("width"),
                "height": video.get("height"),
                "fps": _frame_rate(
                    video.get("avg_frame_rate") or video.get("r_frame_rate")
                ),
                "dynamic_range": _probe_dynamic_range(video),
                "language": _probe_language(audio),
                "filesize": format_info.get("size"),
                "tbr": _kilobits(format_info.get("bit_rate")),
            }
        )
        enriched_formats.append(raw)
    enriched["formats"] = enriched_formats
    return enriched


def enrich_format_metadata(
    raw: dict[str, Any], probe: dict[str, Any]
) -> dict[str, Any]:
    """Fill a single sparse yt-dlp format with bounded ffprobe metadata."""
    probe_streams = probe.get("streams")
    if not isinstance(probe_streams, list):
        return raw

    enriched = dict(raw)
    video = _first_probe_stream(probe_streams, "video")
    audio = _first_probe_stream(probe_streams, "audio")
    if video is None:
        enriched["vcodec"] = "none"
    else:
        enriched.update(
            {
                "vcodec": video.get("codec_name") or enriched.get("vcodec"),
                "width": video.get("width") or enriched.get("width"),
                "height": video.get("height") or enriched.get("height"),
                "fps": _frame_rate(
                    video.get("avg_frame_rate") or video.get("r_frame_rate")
                )
                or enriched.get("fps"),
                "dynamic_range": _probe_dynamic_range(video),
            }
        )
    if audio is None:
        enriched["acodec"] = "none"
    else:
        enriched.update(
            {
                "acodec": audio.get("codec_name") or enriched.get("acodec"),
                "language": _probe_language(audio) or enriched.get("language"),
            }
        )

    format_info = probe.get("format")
    if isinstance(format_info, dict):
        enriched["duration"] = _positive_number(
            format_info.get("duration")
        ) or enriched.get("duration")
        enriched["filesize"] = format_info.get("size") or enriched.get("filesize")
        enriched["tbr"] = _kilobits(format_info.get("bit_rate")) or enriched.get("tbr")
    return enriched


def normalize_metadata(
    payload: dict[str, Any],
    *,
    max_duration_seconds: float,
    max_candidate_streams: int,
) -> MediaInspection:
    _validate_source(payload, max_duration_seconds)
    raw_formats = payload.get("formats")
    if not isinstance(raw_formats, list):
        raise RunnerFailure("unsupported_source")

    streams: list[CandidateStream] = []
    for raw in raw_formats:
        if not isinstance(raw, dict) or raw.get("has_drm") is True:
            continue
        stream = _normalize_stream(raw, payload)
        if stream is None:
            continue
        streams.append(stream)
        if len(streams) > max_candidate_streams:
            raise RunnerFailure("format_limit_exceeded")
    if not streams:
        raise RunnerFailure("format_unavailable", status=409)

    raw_title = str(payload.get("title") or "")
    title = raw_title.strip()
    title_has_control = any(
        ord(character) < 32 or ord(character) == 127 for character in raw_title
    )
    extractor = _identity(
        payload.get("extractor_key") or payload.get("extractor"),
        max_length=128,
    )
    provider_media_id = _identity(payload.get("id"), max_length=256)
    if not title or len(title) > 4096 or title_has_control:
        raise RunnerFailure("invalid_inspection_response", status=502)
    return MediaInspection(
        provider_media_id=provider_media_id,
        title=title,
        duration_seconds=float(payload["duration"]),
        extractor_key=extractor,
        streams=tuple(streams),
        thumbnail_url=_thumbnail_url(payload),
    )


def _thumbnail_url(payload: dict[str, Any]) -> str | None:
    candidates: list[object] = [payload.get("thumbnail")]
    thumbnails = payload.get("thumbnails")
    if isinstance(thumbnails, list):
        candidates.extend(
            value.get("url")
            for value in reversed(thumbnails)
            if isinstance(value, dict)
        )
    for value in candidates:
        if not isinstance(value, str):
            continue
        try:
            return validate_media_url(value).value
        except UrlPolicyError:
            continue
    return None


def _validate_source(payload: dict[str, Any], max_duration: float) -> None:
    media_type = str(payload.get("_type") or "video").casefold()
    if media_type in {"playlist", "multi_video"} or payload.get("entries") is not None:
        raise RunnerFailure("unsupported_source")
    live_status = payload.get("live_status")
    allowed_live_states = {None, "not_live", "was_live"}
    if payload.get("is_live") is True or live_status not in allowed_live_states:
        raise RunnerFailure("unsupported_source")
    if payload.get("has_drm") is True:
        raise RunnerFailure("unsupported_source")
    duration = _positive_number(payload.get("duration"))
    if duration is None:
        raise RunnerFailure("unsupported_source")
    if duration > max_duration:
        raise RunnerFailure("duration_limit_exceeded", status=422)


def _normalize_stream(
    raw: dict[str, Any],
    media: dict[str, Any],
) -> CandidateStream | None:
    raw_provider_id = str(raw.get("format_id") or "")
    if _PROVIDER_ID.fullmatch(raw_provider_id) is None or any(
        ord(character) < 32 or ord(character) == 127 for character in raw_provider_id
    ):
        raise RunnerFailure("invalid_inspection_response", status=502)
    provider_id = raw_provider_id.strip()
    video_codec = str(raw.get("vcodec") or "none")
    audio_codec = str(raw.get("acodec") or "none")
    has_video = video_codec.casefold() != "none"
    has_audio = audio_codec.casefold() != "none"
    if not provider_id or not has_video and not has_audio:
        return None
    kind = (
        StreamKind.MUXED
        if has_video and has_audio
        else StreamKind.VIDEO
        if has_video
        else StreamKind.AUDIO
    )
    height = _positive_int(raw.get("height") or media.get("height"))
    width = _positive_int(raw.get("width") or media.get("width"))
    fps = _positive_number(raw.get("fps") or media.get("fps"))
    language = raw.get("language") or media.get("language")
    bitrate = raw.get("tbr") or raw.get("vbr") or raw.get("abr")
    try:
        return CandidateStream(
            provider_id=provider_id,
            kind=kind,
            container=container_family(raw.get("ext")),
            height=height if has_video else None,
            width=width if has_video else None,
            fps=fps if has_video else None,
            dynamic_range=(
                _dynamic_range(raw.get("dynamic_range")) if has_video else None
            ),
            video_codec_family=video_codec_family(video_codec) if has_video else None,
            audio_codec_family=audio_codec_family(audio_codec) if has_audio else None,
            audio_language=language if has_audio else None,
            bitrate_kbps=_positive_int(bitrate),
            size_bytes=_positive_int(raw.get("filesize") or raw.get("filesize_approx")),
        )
    except (TypeError, ValueError):
        return None


def _positive_number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _positive_int(value: object) -> int | None:
    number = _positive_number(value)
    if number is None:
        return None
    integer = int(number)
    return integer if integer > 0 else None


def _first_probe_stream(
    streams: list[object], stream_type: str
) -> dict[str, Any] | None:
    for stream in streams:
        if isinstance(stream, dict) and stream.get("codec_type") == stream_type:
            return stream
    return None


def _frame_rate(value: object) -> float | None:
    text = str(value or "")
    numerator, separator, denominator = text.partition("/")
    if not separator:
        return _positive_number(text)
    top = _positive_number(numerator)
    bottom = _positive_number(denominator)
    return top / bottom if top is not None and bottom is not None else None


def _kilobits(value: object) -> float | None:
    bits = _positive_number(value)
    return bits / 1000 if bits is not None else None


def _probe_dynamic_range(video: dict[str, Any]) -> str:
    transfer = str(video.get("color_transfer") or "").casefold()
    return "HDR" if transfer in {"smpte2084", "arib-std-b67"} else "SDR"


def _probe_language(audio: dict[str, Any]) -> str | None:
    tags = audio.get("tags")
    language = tags.get("language") if isinstance(tags, dict) else None
    return str(language) if language else None


def _dynamic_range(value: object) -> DynamicRange:
    name = str(value or "SDR").upper()
    return DynamicRange.SDR if name in {"SDR", "SDR10"} else DynamicRange.HDR


def _identity(value: object, *, max_length: int) -> str:
    identity = str(value or "")
    has_control = any(
        ord(character) < 32 or ord(character) == 127 for character in identity
    )
    if not identity or identity != identity.strip() or len(identity) > max_length:
        raise RunnerFailure("invalid_inspection_response", status=502)
    if has_control:
        raise RunnerFailure("invalid_inspection_response", status=502)
    return identity
