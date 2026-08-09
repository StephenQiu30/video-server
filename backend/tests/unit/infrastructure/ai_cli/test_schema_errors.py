from __future__ import annotations

import json

from app.infrastructure.ai_cli.errors import classify_cli_failure
from app.infrastructure.ai_cli.schema import analysis_output_schema


def test_schema_uses_codex_and_claude_supported_subset() -> None:
    schema = analysis_output_schema("visual-analysis.v1", "zh-CN")
    serialized = json.dumps(schema)

    for unsupported in (
        '"$schema"',
        '"uniqueItems"',
        '"minItems"',
        '"maxItems"',
        '"minLength"',
        '"maxLength"',
        '"pattern"',
    ):
        assert unsupported not in serialized
    assert schema["additionalProperties"] is False


def test_claude_max_turns_maps_to_resource_limit() -> None:
    error = classify_cli_failure(
        b'{"subtype":"error_max_turns","terminal_reason":"max_turns"}'
    )

    assert error.code == "analysis_resource_limit"
