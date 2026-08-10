"""Deterministic provider-free visual analysis serialization."""

from typing import Any

from app.domain.analysis import (
    AnalysisMedia,
    AnalysisResult,
    EvidenceSummary,
    Highlight,
    ProductionAdvice,
    Shot,
    VisualAsset,
    validate_analysis_result,
)

_RESULT_FIELDS = {
    "language",
    "title",
    "summary",
    "media",
    "shot_count",
    "shots",
    "highlights",
    "assets",
    "production_advice",
}


def analysis_result_document(result: AnalysisResult) -> dict[str, Any]:
    return {
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
        "production_advice": _production_advice(result.production_advice),
    }


def analysis_result_from_document(document: object) -> AnalysisResult:
    root = _mapping(document, _RESULT_FIELDS, "analysis result")
    summary = _mapping(root["summary"], {"text", "evidence_shot_ids"}, "summary")
    media = _mapping(root["media"], {"duration_ms", "container", "size_bytes"}, "media")
    result = AnalysisResult(
        language=_string(root["language"], "language"),
        title=_string(root["title"], "title"),
        summary=EvidenceSummary(
            text=_string(summary["text"], "summary.text"),
            evidence_shot_ids=_strings(
                summary["evidence_shot_ids"], "summary.evidence_shot_ids"
            ),
        ),
        media=AnalysisMedia(
            duration_ms=_integer(media["duration_ms"], "media.duration_ms"),
            container=_string(media["container"], "media.container"),
            size_bytes=_integer(media["size_bytes"], "media.size_bytes"),
        ),
        shot_count=_integer(root["shot_count"], "shot_count"),
        shots=tuple(_stored_shot(value) for value in _array(root["shots"], "shots")),
        highlights=tuple(
            _stored_highlight(value)
            for value in _array(root["highlights"], "highlights")
        ),
        assets=tuple(
            _stored_asset(value) for value in _array(root["assets"], "assets")
        ),
        production_advice=_stored_production_advice(root["production_advice"]),
    )
    validate_analysis_result(result)
    return result


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
        "narrative_function": value.narrative_function,
        "highlight_score": value.highlight_score,
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


def _production_advice(value: ProductionAdvice) -> dict[str, Any]:
    return {
        "summary": value.summary,
        "priority_shot_ids": list(value.priority_shot_ids),
        "recommended_extensions": list(value.recommended_extensions),
    }


def _stored_shot(value: object) -> Shot:
    source = _mapping(
        value,
        {
            "id",
            "index",
            "start_ms",
            "end_ms",
            "representative_frame_ms",
            "description",
            "transition_in",
            "shot_size",
            "camera_motion",
            "narrative_function",
            "highlight_score",
            "visual_tags",
            "asset_ids",
        },
        "shot",
    )
    return Shot(
        id=_string(source["id"], "shot.id"),
        index=_integer(source["index"], "shot.index"),
        start_ms=_integer(source["start_ms"], "shot.start_ms"),
        end_ms=_integer(source["end_ms"], "shot.end_ms"),
        representative_frame_ms=_integer(
            source["representative_frame_ms"], "shot.representative_frame_ms"
        ),
        description=_string(source["description"], "shot.description"),
        transition_in=_string(source["transition_in"], "shot.transition_in"),
        shot_size=_string(source["shot_size"], "shot.shot_size"),
        camera_motion=_string(source["camera_motion"], "shot.camera_motion"),
        narrative_function=_string(
            source["narrative_function"], "shot.narrative_function"
        ),
        highlight_score=_integer(source["highlight_score"], "shot.highlight_score"),
        visual_tags=_strings(source["visual_tags"], "shot.visual_tags"),
        asset_ids=_strings(source["asset_ids"], "shot.asset_ids"),
    )


def _stored_highlight(value: object) -> Highlight:
    source = _mapping(
        value,
        {
            "id",
            "title",
            "description",
            "score",
            "reason",
            "start_ms",
            "end_ms",
            "evidence_shot_ids",
        },
        "highlight",
    )
    return Highlight(
        id=_string(source["id"], "highlight.id"),
        title=_string(source["title"], "highlight.title"),
        description=_string(source["description"], "highlight.description"),
        score=_integer(source["score"], "highlight.score"),
        reason=_string(source["reason"], "highlight.reason"),
        start_ms=_integer(source["start_ms"], "highlight.start_ms"),
        end_ms=_integer(source["end_ms"], "highlight.end_ms"),
        evidence_shot_ids=_strings(
            source["evidence_shot_ids"], "highlight.evidence_shot_ids"
        ),
    )


def _stored_asset(value: object) -> VisualAsset:
    source = _mapping(
        value,
        {"id", "type", "label", "description", "first_seen_ms", "evidence_shot_ids"},
        "asset",
    )
    return VisualAsset(
        id=_string(source["id"], "asset.id"),
        type=_string(source["type"], "asset.type"),
        label=_string(source["label"], "asset.label"),
        description=_string(source["description"], "asset.description"),
        first_seen_ms=_integer(source["first_seen_ms"], "asset.first_seen_ms"),
        evidence_shot_ids=_strings(
            source["evidence_shot_ids"], "asset.evidence_shot_ids"
        ),
    )


def _stored_production_advice(value: object) -> ProductionAdvice:
    source = _mapping(
        value,
        {"summary", "priority_shot_ids", "recommended_extensions"},
        "production advice",
    )
    return ProductionAdvice(
        summary=_string(source["summary"], "production_advice.summary"),
        priority_shot_ids=_strings(
            source["priority_shot_ids"], "production_advice.priority_shot_ids"
        ),
        recommended_extensions=_strings(
            source["recommended_extensions"],
            "production_advice.recommended_extensions",
        ),
    )


def _mapping(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"stored {label} has an invalid shape")
    return value


def _array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"stored {label} must be an array")
    return value


def _strings(value: object, label: str) -> tuple[str, ...]:
    return tuple(_string(item, label) for item in _array(value, label))


def _string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"stored {label} must be a string")
    return value


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"stored {label} must be an integer")
    return value
