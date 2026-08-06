from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from app.domain.downloads import (
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DownloadPlan,
    DynamicRange,
    FpsBucket,
    ProviderHints,
    VideoCodecFamily,
)


def plan_to_documents(
    plan: DownloadPlan,
) -> tuple[dict[str, object], dict[str, object]]:
    semantic: dict[str, object] = {
        "height": plan.height,
        "width": plan.width,
        "fps_bucket": plan.fps_bucket.value,
        "dynamic_range": plan.dynamic_range.value,
        "video_codec_family": plan.video_codec_family.value,
        "audio_codec_family": plan.audio_codec_family.value,
        "audio_language": plan.audio_language,
        "container_preference": plan.container_preference.value,
        "compatibility_profile": plan.compatibility_profile.value,
    }
    hints: dict[str, object] = {
        "video_id": plan.hints.video_id,
        "audio_id": plan.hints.audio_id,
    }
    return semantic, hints


def plan_from_documents(
    semantic: dict[str, object], hints: dict[str, object]
) -> DownloadPlan:
    return DownloadPlan(
        height=_integer(semantic, "height"),
        width=_integer(semantic, "width"),
        fps_bucket=FpsBucket(_string(semantic, "fps_bucket")),
        dynamic_range=DynamicRange(_string(semantic, "dynamic_range")),
        video_codec_family=VideoCodecFamily(_string(semantic, "video_codec_family")),
        audio_codec_family=AudioCodecFamily(_string(semantic, "audio_codec_family")),
        audio_language=_optional_string(semantic, "audio_language"),
        container_preference=ContainerPreference(
            _string(semantic, "container_preference")
        ),
        compatibility_profile=CompatibilityProfile(
            _string(semantic, "compatibility_profile")
        ),
        hints=ProviderHints(
            video_id=_optional_string(hints, "video_id"),
            audio_id=_optional_string(hints, "audio_id"),
        ),
    )


def public_plan(plan: DownloadPlan) -> DownloadPlan:
    return replace(plan, hints=ProviderHints())


def plan_fingerprint(semantic: dict[str, object]) -> str:
    encoded = json.dumps(
        semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _string(document: dict[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(document: dict[str, object], key: str) -> str | None:
    value = document.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a string or null")
    return value


def _integer(document: dict[str, object], key: str) -> int:
    value = document.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value
