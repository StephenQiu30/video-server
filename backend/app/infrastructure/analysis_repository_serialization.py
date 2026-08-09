"""Deterministic provider-free visual analysis serialization."""

from typing import Any

from app.domain.analysis import (
    AnalysisResult,
    EvidenceSummary,
    Highlight,
    Shot,
    VisualAsset,
)


def analysis_result_document(result: AnalysisResult) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "language": result.language,
        "title": result.title,
        "summary": _summary(result.summary),
        "media": {
            "duration_ms": result.media.duration_ms,
            "container": result.media.container,
            "size_bytes": result.media.size_bytes,
        },
        "shot_count": result.shot_count,
        "shots": [_shot(item) for item in result.shots],
        "highlights": [_highlight(item) for item in result.highlights],
        "assets": [_asset(item) for item in result.assets],
    }


def _summary(value: EvidenceSummary) -> dict[str, Any]:
    return {"text": value.text, "evidence_shot_ids": list(value.evidence_shot_ids)}


def _shot(value: Shot) -> dict[str, Any]:
    return {
        "id": value.id,
        "index": value.index,
        "start_ms": value.start_ms,
        "end_ms": value.end_ms,
        "representative_frame_ms": value.representative_frame_ms,
        "description": value.description,
        "transition_in": value.transition_in,
        "shot_size": value.shot_size,
        "camera_motion": value.camera_motion,
        "visual_tags": list(value.visual_tags),
        "asset_ids": list(value.asset_ids),
    }


def _highlight(value: Highlight) -> dict[str, Any]:
    return {
        "id": value.id,
        "title": value.title,
        "description": value.description,
        "score": value.score,
        "reason": value.reason,
        "start_ms": value.start_ms,
        "end_ms": value.end_ms,
        "evidence_shot_ids": list(value.evidence_shot_ids),
    }


def _asset(value: VisualAsset) -> dict[str, Any]:
    return {
        "id": value.id,
        "type": value.type,
        "label": value.label,
        "description": value.description,
        "first_seen_ms": value.first_seen_ms,
        "evidence_shot_ids": list(value.evidence_shot_ids),
    }
