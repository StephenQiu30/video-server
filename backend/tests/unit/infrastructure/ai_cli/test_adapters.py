from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from app.infrastructure.ai_cli import (
    AnalysisCliError,
    ClaudeCliVideoAnalyzer,
    CliAdapterConfig,
    CodexCliVideoAnalyzer,
)
from tests.unit.infrastructure.ai_cli.helpers import (
    FakeSupervisor,
    request,
    screenplay_glossary_request,
    screenplay_request,
    screenplay_rewrite_chunk_request,
    screenplay_supervisor,
)
from tests.unit.workers.analysis.fixtures import (
    valid_mapping,
    valid_screenplay_mapping,
)


def config() -> CliAdapterConfig:
    return CliAdapterConfig(
        binary=Path(sys.executable),
        model="controlled-model",
        ffmpeg=Path(sys.executable),
        ffprobe=Path(sys.executable),
    )


@pytest.mark.asyncio
async def test_codex_uses_stdin_and_global_approval_flag(tmp_path: Path) -> None:
    supervisor = FakeSupervisor(provider="codex")
    analyzer = CodexCliVideoAnalyzer(config(), supervisor=supervisor)  # type: ignore[arg-type]

    payload = await analyzer.analyze(request(tmp_path))

    assert payload == valid_mapping()
    assert supervisor.argv[:4] == (
        sys.executable,
        "--ask-for-approval",
        "never",
        "--strict-config",
    )
    assert "exec" in supervisor.argv
    assert supervisor.argv.index("--ignore-user-config") < supervisor.argv.index(
        'default_permissions="video_analysis"'
    )
    assert "--sandbox" not in supervisor.argv
    assert 'default_permissions="video_analysis"' in supervisor.argv
    assert not any("danger-full-access" in item for item in supervisor.argv)
    assert any(":workspace_roots" in item for item in supervisor.argv)
    assert "permissions.video_analysis.network.enabled=false" in supervisor.argv
    assert "mcp_servers.video_observer.required=true" in supervisor.argv
    assert any(
        item.startswith("mcp_servers.video_observer.enabled_tools=[")
        for item in supervisor.argv
    )
    assert supervisor.argv[-1] == "-"
    assert supervisor.input_bytes is not None
    assert b"input/video.bin" in supervisor.input_bytes
    assert "完整视频已通过 video_observer 工具交给你".encode() in supervisor.input_bytes
    assert all("input/video.bin" not in item for item in supervisor.argv)
    assert _has_no_api_keys(supervisor.environment)


@pytest.mark.asyncio
async def test_claude_returns_structured_output_without_prompt_argv(
    tmp_path: Path,
) -> None:
    supervisor = FakeSupervisor(provider="claude")
    analyzer = ClaudeCliVideoAnalyzer(config(), supervisor=supervisor)  # type: ignore[arg-type]

    payload = await analyzer.analyze(request(tmp_path))

    assert payload == valid_mapping()
    assert "--safe-mode" in supervisor.argv
    assert "--strict-mcp-config" in supervisor.argv
    assert "--json-schema" in supervisor.argv
    assert supervisor.input_bytes is not None
    assert b"input/video.bin" in supervisor.input_bytes
    assert all("input/video.bin" not in item for item in supervisor.argv)
    assert _has_no_api_keys(supervisor.environment)


@pytest.mark.asyncio
async def test_claude_screenplay_is_single_turn_and_disables_all_tools(
    tmp_path: Path,
) -> None:
    supervisor = screenplay_supervisor()
    analyzer = ClaudeCliVideoAnalyzer(config(), supervisor=supervisor)  # type: ignore[arg-type]
    screenplay = screenplay_request(tmp_path)

    payload = await analyzer.analyze_screenplay(screenplay)

    assert payload == valid_screenplay_mapping()
    assert supervisor.argv[supervisor.argv.index("--tools") + 1] == ""
    assert supervisor.argv[supervisor.argv.index("--max-turns") + 1] == "1"
    assert "--allowedTools" not in supervisor.argv
    assert "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent" in supervisor.argv
    assert supervisor.input_bytes is not None
    encoded = json.dumps(screenplay.screenplay_text, ensure_ascii=False).encode()
    assert encoded in supervisor.input_bytes
    assert all(screenplay.screenplay_text not in value for value in supervisor.argv)
    assert _has_no_api_keys(supervisor.environment)


@pytest.mark.asyncio
async def test_claude_screenplay_rejects_oversized_schema_before_process(
    tmp_path: Path,
) -> None:
    supervisor = screenplay_supervisor()
    analyzer = ClaudeCliVideoAnalyzer(config(), supervisor=supervisor)  # type: ignore[arg-type]
    screenplay = screenplay_request(tmp_path)
    screenplay = replace(
        screenplay,
        source_scene_ids=tuple(
            f"scene-{index:04d}-{'a' * 110}" for index in range(1, 121)
        ),
    )

    with pytest.raises(AnalysisCliError) as error:
        await analyzer.analyze_screenplay(screenplay)

    assert error.value.code == "analysis_resource_limit"
    assert supervisor.argv == ()


@pytest.mark.asyncio
async def test_claude_builds_screenplay_glossary_without_tools(tmp_path: Path) -> None:
    payload = {
        "source_language": "mixed",
        "target_language": "en-US",
        "terms": [{"source": "林舟", "target": "Lin Zhou", "category": "character"}],
        "style_rules": ["Use concise screenplay English."],
    }
    supervisor = FakeSupervisor(provider="claude", payload=payload)
    analyzer = ClaudeCliVideoAnalyzer(config(), supervisor=supervisor)  # type: ignore[arg-type]
    request_value = screenplay_glossary_request(tmp_path)

    result = await analyzer.build_screenplay_glossary(request_value)

    assert result == payload
    assert supervisor.argv[supervisor.argv.index("--tools") + 1] == ""
    assert supervisor.argv[supervisor.argv.index("--max-turns") + 1] == "1"
    assert supervisor.input_bytes is not None
    assert (
        json.dumps(request_value.screenplay_text, ensure_ascii=False).encode()
        in supervisor.input_bytes
    )


@pytest.mark.asyncio
async def test_claude_rewrites_one_hash_bound_chunk_without_tools(
    tmp_path: Path,
) -> None:
    request_value = screenplay_rewrite_chunk_request(tmp_path)
    payload = {
        "source_scene_id": request_value.source_scene_id,
        "part_no": request_value.part_no,
        "source_sha256": request_value.source_sha256,
        "target_language": request_value.target_language,
        "rewritten_text": "LIN ZHOU discovers that the ending is missing.\n",
        "change_summary": ["Localized the character name."],
    }
    supervisor = FakeSupervisor(provider="claude", payload=payload)
    analyzer = ClaudeCliVideoAnalyzer(config(), supervisor=supervisor)  # type: ignore[arg-type]

    result = await analyzer.rewrite_screenplay_chunk(request_value)

    assert result == payload
    assert supervisor.argv[supervisor.argv.index("--tools") + 1] == ""
    assert supervisor.input_bytes is not None
    assert (
        json.dumps(request_value.source_text, ensure_ascii=False).encode()
        in supervisor.input_bytes
    )
    manifest = json.loads(
        (request_value.workspace / "input" / "manifest.json").read_text()
    )
    assert manifest["source_sha256"] == request_value.source_sha256
    assert "rewritten_text" not in manifest


def _has_no_api_keys(environment: dict[str, str]) -> bool:
    forbidden = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
    }
    return forbidden.isdisjoint(environment)
