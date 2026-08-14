import json
from pathlib import Path

from app.infrastructure.ai_cli.screenplay_rewrite_prompt import (
    screenplay_glossary_prompt,
    screenplay_rewrite_chunk_prompt,
)
from app.infrastructure.ai_cli.screenplay_rewrite_schema import (
    screenplay_glossary_output_schema,
    screenplay_rewrite_chunk_output_schema,
)
from tests.unit.infrastructure.ai_cli.helpers import (
    screenplay_glossary_request,
    screenplay_rewrite_chunk_request,
)


def test_glossary_schema_is_strict_and_language_bound() -> None:
    schema = screenplay_glossary_output_schema("mixed", "en-US")

    assert schema["additionalProperties"] is False
    properties = schema["properties"]
    assert properties["source_language"]["enum"] == ["mixed"]
    assert properties["target_language"]["enum"] == ["en-US"]
    term = properties["terms"]["items"]
    assert term["additionalProperties"] is False
    assert "character" in term["properties"]["category"]["enum"]


def test_chunk_schema_binds_all_source_identity_fields(tmp_path: Path) -> None:
    request = screenplay_rewrite_chunk_request(tmp_path)
    schema = screenplay_rewrite_chunk_output_schema(
        source_scene_id=request.source_scene_id,
        part_no=request.part_no,
        source_sha256=request.source_sha256,
        target_language=request.target_language,
    )

    properties = schema["properties"]
    assert properties["source_scene_id"]["enum"] == [request.source_scene_id]
    assert properties["part_no"]["enum"] == [request.part_no]
    assert properties["source_sha256"]["enum"] == [request.source_sha256]
    assert properties["target_language"]["enum"] == [request.target_language]


def test_rewrite_prompts_json_escape_untrusted_content(tmp_path: Path) -> None:
    glossary = screenplay_glossary_request(tmp_path)
    chunk = screenplay_rewrite_chunk_request(tmp_path)

    glossary_prompt = screenplay_glossary_prompt(glossary)
    chunk_prompt = screenplay_rewrite_chunk_prompt(chunk)

    assert json.dumps(glossary.screenplay_text, ensure_ascii=False) in glossary_prompt
    assert json.dumps(chunk.source_text, ensure_ascii=False) in chunk_prompt
    assert "glossary 已通过服务端结构校验" in chunk_prompt
    assert "不得访问工具、文件、网络" in glossary_prompt
    assert "不得访问工具、文件、网络" in chunk_prompt
