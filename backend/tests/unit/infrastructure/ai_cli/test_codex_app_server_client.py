# ruff: noqa: E501

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from app.infrastructure.ai_cli.codex_app_server_client import CodexAppServerClient
from app.infrastructure.ai_cli.config import CliAdapterConfig
from app.infrastructure.ai_cli.errors import AnalysisCliError


def config(binary: Path) -> CliAdapterConfig:
    return CliAdapterConfig(
        binary=binary,
        model="controlled-model",
        ffmpeg=Path(sys.executable),
        ffprobe=Path(sys.executable),
        timeout_seconds=5,
    )


def fake_server(tmp_path: Path, *, failure: str | None = None) -> Path:
    script = tmp_path / "fake-codex"
    failure_literal = repr(failure)
    script.write_text(
        f"""#!{sys.executable}
import json
import sys

failure = {failure_literal}
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    if method == "initialize":
        assert message["params"]["clientInfo"]["name"] == "video_server"
        assert message["params"]["capabilities"]["experimentalApi"] is True
        print(json.dumps({{"id": 1, "result": {{"userAgent": "fake"}}}}), flush=True)
    elif method == "initialized":
        continue
    elif method == "thread/start":
        if failure == "schema":
            print(json.dumps({{"id": 2, "error": {{"message": "invalid_json_schema"}}}}), flush=True)
            continue
        params = message["params"]
        assert params["ephemeral"] is True
        assert params["approvalPolicy"] == "never"
        assert params["permissions"] == "video_analysis"
        print(json.dumps({{"id": 2, "result": {{"thread": {{"id": "thread-1"}}}}}}), flush=True)
    elif method == "turn/start":
        params = message["params"]
        assert params["threadId"] == "thread-1"
        assert params["outputSchema"]["type"] == "object"
        print(json.dumps({{"id": 3, "result": {{"turn": {{"id": "turn-1"}}}}}}), flush=True)
        if failure == "rate":
            turn = {{"id": "turn-1", "status": "failed", "items": [], "error": {{"message": "429 rate limit"}}}}
        else:
            item = {{"type": "agentMessage", "id": "item-1", "text": '{{"answer":"ok"}}'}}
            print(json.dumps({{"method": "item/completed", "params": {{"item": item}}}}), flush=True)
            turn = {{"id": "turn-1", "status": "completed", "items": [item], "error": None}}
        print(json.dumps({{"method": "turn/completed", "params": {{"threadId": "thread-1", "turn": turn}}}}), flush=True)
""",
        encoding="utf-8",
    )
    script.chmod(0o700)
    return script


@pytest.mark.asyncio
async def test_client_runs_ephemeral_structured_app_server_turn(
    tmp_path: Path,
) -> None:
    root = tmp_path / "job"
    (root / "tmp").mkdir(parents=True)
    client = CodexAppServerClient(config(fake_server(tmp_path)))

    result = await client.invoke(
        root=root,
        prompt="analyze",
        schema={"type": "object"},
        duration_ms=None,
    )

    assert result == {"answer": "ok"}
    command = client.command(root, None)
    assert "app-server" in command
    assert "stdio://" in command
    assert "exec" not in command
    assert "mcp_servers={}" in command
    assert 'default_permissions="video_analysis"' in command
    assert not any("video_observer" in item for item in command)


def test_video_turn_enables_only_the_scoped_observer(tmp_path: Path) -> None:
    client = CodexAppServerClient(config(fake_server(tmp_path)))

    command = client.command(tmp_path, 2_000)

    assert "mcp_servers.video_observer.required=true" in command
    assert any(
        value.startswith("mcp_servers.video_observer.enabled_tools=[")
        for value in command
    )
    assert "permissions.video_analysis.network.enabled=false" in command


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "code"),
    (
        ("schema", "analysis_cli_unsupported"),
        ("rate", "analysis_provider_rate_limited"),
    ),
)
async def test_client_maps_app_server_failures(
    tmp_path: Path, failure: str, code: str
) -> None:
    root = tmp_path / "job"
    (root / "tmp").mkdir(parents=True)
    client = CodexAppServerClient(config(fake_server(tmp_path, failure=failure)))

    with pytest.raises(AnalysisCliError) as error:
        await client.invoke(
            root=root,
            prompt="analyze",
            schema={"type": "object"},
            duration_ms=None,
        )

    assert error.value.code == code
