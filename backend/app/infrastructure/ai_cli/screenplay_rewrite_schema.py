from __future__ import annotations

from typing import Any

_CATEGORIES = ["character", "location", "term", "title", "honorific", "other"]


def screenplay_glossary_output_schema(
    source_language: str, target_language: str
) -> dict[str, Any]:
    _validate_languages(source_language, target_language)
    term = _object(
        ["source", "target", "category"],
        {
            "source": _text(),
            "target": _text(),
            "category": {"type": "string", "enum": _CATEGORIES},
        },
    )
    return _object(
        ["source_language", "target_language", "terms", "style_rules"],
        {
            "source_language": {"type": "string", "enum": [source_language]},
            "target_language": {"type": "string", "enum": [target_language]},
            "terms": _array(term),
            "style_rules": _array(_short_text(), minimum=1, maximum=64),
        },
    )


def screenplay_rewrite_chunk_output_schema(
    *,
    source_scene_id: str,
    part_no: int,
    source_sha256: str,
    target_language: str,
) -> dict[str, Any]:
    if (
        not source_scene_id.startswith("scene-")
        or isinstance(part_no, bool)
        or not isinstance(part_no, int)
        or part_no <= 0
        or len(source_sha256) != 64
        or any(value not in "0123456789abcdef" for value in source_sha256)
        or target_language not in {"zh-CN", "en-US"}
    ):
        raise ValueError("screenplay rewrite chunk schema inputs are invalid")
    return _object(
        [
            "source_scene_id",
            "part_no",
            "source_sha256",
            "target_language",
            "rewritten_text",
            "change_summary",
        ],
        {
            "source_scene_id": {"type": "string", "enum": [source_scene_id]},
            "part_no": {"type": "integer", "enum": [part_no]},
            "source_sha256": {"type": "string", "enum": [source_sha256]},
            "target_language": {"type": "string", "enum": [target_language]},
            "rewritten_text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 200_000,
            },
            "change_summary": _array(_short_text(), minimum=1, maximum=64),
        },
    )


def _validate_languages(source_language: str, target_language: str) -> None:
    if source_language not in {
        "zh-CN",
        "en-US",
        "mixed",
        "unknown",
    } or target_language not in {"zh-CN", "en-US"}:
        raise ValueError("screenplay rewrite schema languages are invalid")


def _array(
    items: dict[str, Any], *, minimum: int = 0, maximum: int = 512
) -> dict[str, Any]:
    return {
        "type": "array",
        "minItems": minimum,
        "maxItems": maximum,
        "items": items,
    }


def _object(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def _text() -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": 8_000}


def _short_text() -> dict[str, Any]:
    return {"type": "string", "minLength": 1, "maxLength": 128}
