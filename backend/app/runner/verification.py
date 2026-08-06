from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.domain.downloads import Container, DownloadPlan
from app.runner.codecs import audio_codec_family, video_codec_family
from app.runner.errors import RunnerFailure


@dataclass(frozen=True, slots=True)
class VerifiedProbe:
    duration_seconds: float
    video_streams: int
    audio_streams: int


def verify_probe(
    payload: dict[str, Any],
    *,
    plan: DownloadPlan,
    expected_container: Container,
    expected_duration: float,
    max_duration: float,
    tolerance_seconds: float,
) -> VerifiedProbe:
    format_info = payload.get("format")
    streams = payload.get("streams")
    if not isinstance(format_info, dict) or not isinstance(streams, list):
        raise RunnerFailure("media_validation_failed", status=502)
    if not _container_matches(format_info.get("format_name"), expected_container):
        raise RunnerFailure("media_validation_failed", status=502)

    video = [item for item in streams if _stream_type(item) == "video"]
    audio = [item for item in streams if _stream_type(item) == "audio"]
    if not video or not audio:
        raise RunnerFailure("media_validation_failed", status=502)
    first_video = video[0]
    first_audio = audio[0]
    dimensions = (first_video.get("width"), first_video.get("height"))
    if dimensions != (plan.width, plan.height):
        raise RunnerFailure("media_validation_failed", status=502)
    if video_codec_family(first_video.get("codec_name")) is not plan.video_codec_family:
        raise RunnerFailure("media_validation_failed", status=502)
    if audio_codec_family(first_audio.get("codec_name")) is not plan.audio_codec_family:
        raise RunnerFailure("media_validation_failed", status=502)

    duration = _duration(format_info.get("duration"))
    tolerance = max(tolerance_seconds, expected_duration * 0.02)
    if duration is None or duration > max_duration:
        raise RunnerFailure("media_validation_failed", status=502)
    if abs(duration - expected_duration) > tolerance:
        raise RunnerFailure("media_validation_failed", status=502)
    return VerifiedProbe(duration, len(video), len(audio))


def _stream_type(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    stream_type = value.get("codec_type")
    return stream_type if isinstance(stream_type, str) else None


def _container_matches(value: object, expected: Container) -> bool:
    names = {name.strip() for name in str(value or "").casefold().split(",")}
    if expected is Container.MP4:
        return bool(names & {"mp4", "mov", "m4a", "3gp", "3g2", "mj2"})
    if expected is Container.WEBM:
        return bool(names & {"webm", "matroska"})
    return False


def _duration(value: object) -> float | None:
    try:
        duration = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return duration if math.isfinite(duration) and duration > 0 else None
