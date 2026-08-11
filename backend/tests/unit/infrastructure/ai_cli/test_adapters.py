from __future__ import annotations

import sys
from pathlib import Path

import pytest
from app.infrastructure.ai_cli import (
    ClaudeCliVideoAnalyzer,
    CliAdapterConfig,
    CodexCliVideoAnalyzer,
)
from tests.unit.infrastructure.ai_cli.helpers import FakeSupervisor, request
from tests.unit.workers.analysis.fixtures import valid_mapping


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
    assert 'sandbox_mode="danger-full-access"' in supervisor.argv
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


def _has_no_api_keys(environment: dict[str, str]) -> bool:
    forbidden = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
    }
    return forbidden.isdisjoint(environment)
