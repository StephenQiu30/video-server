"""Deduplicate, recommend, and order normalized format candidates."""

from __future__ import annotations

from typing import Any

from video_server.source._format_types import NormalizedFormat, family


def _recommendation_key(item: NormalizedFormat) -> tuple[Any, ...]:
    def capped(value: float | int | None, limit: float) -> tuple[int, float]:
        if value is None:
            return (2, 0)
        return (0, -float(value)) if value <= limit else (1, float(value))

    return (
        len(item.component_ids) == 2,
        family(item.container) != "mp4",
        item.video_codec != "h264",
        item.audio_codec != "aac",
        capped(item.height, 1080),
        capped(item.fps, 60),
        item.estimated_bytes is None,
        item.fingerprint_sha256,
    )


def _deduplicate(candidates: list[NormalizedFormat]) -> list[NormalizedFormat]:
    groups: dict[tuple[Any, ...], list[NormalizedFormat]] = {}
    for item in candidates:
        key = (
            item.width,
            item.height,
            item.fps,
            item.dynamic_range,
            item.video_codec,
            item.audio_codec,
            item.container,
            len(item.component_ids) == 2,
        )
        groups.setdefault(key, []).append(item)
    return [
        min(
            group,
            key=lambda item: (
                item.estimated_bytes is None or item.size_is_estimate,
                -item.total_bitrate,
                item.component_ids[0].encode(),
                (item.component_ids[1] if len(item.component_ids) == 2 else "").encode(),
                item.fingerprint_sha256,
            ),
        )
        for group in groups.values()
    ]


def deduplicate_and_sort(candidates: list[NormalizedFormat]) -> list[NormalizedFormat]:
    candidates = _deduplicate(candidates)
    if candidates:
        min(candidates, key=_recommendation_key).recommended = True
    candidates.sort(
        key=lambda item: (
            not item.recommended,
            item.height is None,
            -(item.height or 0),
            item.fps is None,
            -(item.fps or 0),
            len(item.component_ids) == 2,
            {"mp4": 0, "webm": 1}.get(family(item.container) or "", 2),
            item.estimated_bytes is None,
            item.estimated_bytes or 0,
            item.fingerprint_sha256,
        )
    )
    return candidates
