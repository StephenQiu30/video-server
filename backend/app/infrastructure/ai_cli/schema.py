from __future__ import annotations

from typing import Any

from app.domain.analysis import AnalysisResultContract


def analysis_output_schema(
    language: str,
    result_contract: AnalysisResultContract = (
        AnalysisResultContract.VIDEO_VISUAL_ANALYSIS
    ),
) -> dict[str, Any]:
    if result_contract is AnalysisResultContract.VIDEO_ARTICLE:
        return video_article_output_schema(language)
    reference_array = {
        "type": "array",
        "items": {"type": "string"},
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "language",
            "title",
            "summary",
            "shots",
            "highlights",
            "assets",
            "production_advice",
        ],
        "properties": {
            "language": {"type": "string", "enum": [language]},
            "title": _text(),
            "summary": _object(
                ["text", "evidence_shot_ids"],
                {"text": _text(), "evidence_shot_ids": reference_array},
            ),
            "shots": {
                "type": "array",
                "items": _shot(),
            },
            "highlights": {
                "type": "array",
                "items": _highlight(reference_array),
            },
            "assets": {
                "type": "array",
                "items": _asset(reference_array),
            },
            "production_advice": _production_advice(reference_array),
        },
    }


def video_article_output_schema(language: str) -> dict[str, Any]:
    evidence = _object(
        ["start_ms", "end_ms", "note"],
        {"start_ms": _integer(), "end_ms": _integer(), "note": _text()},
    )
    section = _object(
        ["id", "title", "body", "evidence"],
        {
            "id": _identifier(),
            "title": _text(),
            "body": _text(),
            "evidence": {"type": "array", "minItems": 1, "items": evidence},
        },
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "language",
            "title",
            "lead",
            "sections",
            "key_points",
            "closing",
            "limitations",
        ],
        "properties": {
            "language": {"type": "string", "enum": [language]},
            "title": _text(),
            "lead": _text(),
            "sections": {"type": "array", "minItems": 1, "items": section},
            "key_points": {"type": "array", "minItems": 1, "items": _text()},
            "closing": _text(),
            "limitations": {"type": "array", "items": _text()},
        },
    }


def _shot() -> dict[str, Any]:
    fields = [
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
    ]
    return _object(
        fields,
        {
            "id": _identifier(),
            "index": _integer(),
            "start_ms": _integer(),
            "end_ms": _integer(),
            "representative_frame_ms": _integer(),
            "description": _text(),
            "transition_in": {
                "enum": ["cut", "fade", "dissolve", "wipe", "none", "unknown"]
            },
            "shot_size": {
                "enum": [
                    "extreme_wide",
                    "wide",
                    "medium",
                    "close_up",
                    "extreme_close_up",
                    "mixed",
                    "unknown",
                ]
            },
            "camera_motion": {
                "enum": [
                    "static",
                    "pan",
                    "tilt",
                    "zoom",
                    "dolly",
                    "tracking",
                    "handheld",
                    "mixed",
                    "unknown",
                ]
            },
            "narrative_function": _text(),
            "highlight_score": {"type": "integer", "minimum": 1, "maximum": 5},
            "visual_tags": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    )


def _highlight(references: dict[str, Any]) -> dict[str, Any]:
    fields = ["id", "title", "description", "score", "reason", "evidence_shot_ids"]
    return _object(
        fields,
        {
            "id": _identifier(),
            "title": _text(),
            "description": _text(),
            "score": {"type": "integer"},
            "reason": _text(),
            "evidence_shot_ids": references,
        },
    )


def _asset(references: dict[str, Any]) -> dict[str, Any]:
    fields = ["id", "type", "label", "description", "evidence_shot_ids"]
    return _object(
        fields,
        {
            "id": _identifier(),
            "type": {
                "enum": [
                    "person",
                    "location",
                    "object",
                    "product",
                    "logo",
                    "on_screen_text",
                ]
            },
            "label": _text(),
            "description": _text(),
            "evidence_shot_ids": references,
        },
    )


def _production_advice(references: dict[str, Any]) -> dict[str, Any]:
    fields = ["summary", "priority_shot_ids", "recommended_extensions"]
    return _object(
        fields,
        {
            "summary": _text(),
            "priority_shot_ids": references,
            "recommended_extensions": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    )


def _object(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _identifier() -> dict[str, Any]:
    return {"type": "string"}


def _text() -> dict[str, Any]:
    return {"type": "string"}


def _integer() -> dict[str, Any]:
    return {"type": "integer"}
