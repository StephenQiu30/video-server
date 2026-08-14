from __future__ import annotations

from typing import Any

from app.application.analysis_execution import SCREENPLAY_SINGLE_CALL_SCENE_LIMIT


def screenplay_analysis_output_schema(
    language: str, source_scene_ids: tuple[str, ...]
) -> dict[str, Any]:
    if (
        language not in {"zh-CN", "en-US"}
        or not source_scene_ids
        or len(source_scene_ids) > SCREENPLAY_SINGLE_CALL_SCENE_LIMIT
        or len(set(source_scene_ids)) != len(source_scene_ids)
    ):
        raise ValueError("screenplay schema inputs are invalid")
    references = _references(source_scene_ids)
    evidence = _evidence_item(references)
    return _object(
        [
            "language",
            "title",
            "logline",
            "synopsis",
            "structure",
            "characters",
            "scenes",
            "dialogue_findings",
            "strengths",
            "priority_revisions",
        ],
        {
            "language": {"type": "string", "enum": [language]},
            "title": _text(),
            "logline": _text(),
            "synopsis": _text(),
            "structure": _object(
                ["acts", "turning_points", "pacing_summary"],
                {
                    "acts": _array(evidence, minimum=1),
                    "turning_points": _array(evidence),
                    "pacing_summary": _text(),
                },
            ),
            "characters": _array(_character(references)),
            "scenes": {
                "type": "array",
                "minItems": len(source_scene_ids),
                "maxItems": len(source_scene_ids),
                "items": _scene(source_scene_ids),
            },
            "dialogue_findings": _array(evidence),
            "strengths": _array(evidence, minimum=1),
            "priority_revisions": _array(evidence, minimum=1),
        },
    )


def _evidence_item(references: dict[str, Any]) -> dict[str, Any]:
    return _object(
        ["id", "title", "description", "evidence_scene_ids"],
        {
            "id": _identifier(),
            "title": _text(),
            "description": _text(),
            "evidence_scene_ids": references,
        },
    )


def _character(references: dict[str, Any]) -> dict[str, Any]:
    return _object(
        ["id", "name", "goal", "conflict", "arc", "evidence_scene_ids"],
        {
            "id": _identifier(),
            "name": _text(),
            "goal": _text(),
            "conflict": _text(),
            "arc": _text(),
            "evidence_scene_ids": references,
        },
    )


def _scene(source_scene_ids: tuple[str, ...]) -> dict[str, Any]:
    return _object(
        [
            "id",
            "source_scene_id",
            "purpose",
            "conflict",
            "turn",
            "pacing",
            "findings",
        ],
        {
            "id": _identifier(),
            "source_scene_id": {
                "type": "string",
                "enum": list(source_scene_ids),
            },
            "purpose": _text(),
            "conflict": _text(),
            "turn": _text(),
            "pacing": _text(),
            "findings": _array(_short_text()),
        },
    )


def _references(source_scene_ids: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": min(512, len(source_scene_ids)),
        "uniqueItems": True,
        "items": {"type": "string", "enum": list(source_scene_ids)},
    }


def _array(items: dict[str, Any], *, minimum: int = 0) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": minimum,
        "maxItems": 512,
        "items": items,
    }


def _object(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _identifier() -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": 128, "pattern": r"^\S+$"}


def _text() -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": 8_000}


def _short_text() -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": 128}
