from __future__ import annotations

from typing import Any


def analysis_output_schema(schema_version: str, language: str) -> dict[str, Any]:
    reference_array = {
        "type": "array",
        "items": {"type": "string"},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "language",
            "title",
            "summary",
            "shots",
            "highlights",
            "assets",
        ],
        "properties": {
            "schema_version": {"type": "string", "enum": [schema_version]},
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
