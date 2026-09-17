from __future__ import annotations

import ast
import importlib.util
import json
import os
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
AGENT_SCRIPT = REPOSITORY_ROOT / "plugins/framefetch/scripts/framefetch_agent.py"
MCP_SCRIPT = REPOSITORY_ROOT / "plugins/framefetch/scripts/framefetch_mcp.py"
MCP_MANIFEST = REPOSITORY_ROOT / "plugins/framefetch/.mcp.json"


def _load_agent_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("framefetch_agent_test", AGENT_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _completed(
    command: list[str], returncode: int, stdout: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, "")


def test_plugin_distribution_is_backend_and_secret_independent() -> None:
    imported_modules: set[str] = set()
    for script in (AGENT_SCRIPT, MCP_SCRIPT):
        tree = ast.parse(script.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)

    manifest = json.loads(MCP_MANIFEST.read_text(encoding="utf-8"))
    inherited_variables = set(manifest["mcpServers"]["framefetch"]["env_vars"])

    backend_imports = {
        module
        for module in imported_modules
        if module == "app" or module.startswith("app.")
    }
    assert backend_imports == set()
    assert inherited_variables.isdisjoint(
        {
            "DATABASE_URL",
            "RABBITMQ_PASSWORD",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "OPENROUTER_API_KEY",
        }
    )


def test_diagnostics_distinguish_ready_login_required_and_missing() -> None:
    agent = _load_agent_module()

    def which(name: str) -> str | None:
        return {"codex": "/tools/codex", "claude": "/tools/claude"}.get(name)

    def runner(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command == ["/tools/codex", "--version"]:
            return _completed(command, 0, "codex-cli 1.2.3\n")
        if command == ["/tools/codex", "login", "status"]:
            return _completed(command, 0, "Logged in\n")
        if command == ["/tools/claude", "--version"]:
            return _completed(command, 0, "2.0.0 (Claude Code)\n")
        if command == ["/tools/claude", "auth", "status", "--json"]:
            return _completed(
                command,
                1,
                '{"loggedIn":false,"email":"hidden@example.com"}',
            )
        raise AssertionError(command)

    result = agent.collect_diagnostics(which=which, runner=runner)

    assert result["providers"]["codex"] == {
        "installed": True,
        "version": "codex-cli 1.2.3",
        "authenticated": True,
        "status": "ready",
    }
    assert result["providers"]["claude"] == {
        "installed": True,
        "version": "2.0.0 (Claude Code)",
        "authenticated": False,
        "status": "login_required",
    }
    assert "hidden@example.com" not in json.dumps(result)

    missing = agent.collect_diagnostics(which=lambda _name: None, runner=runner)
    assert missing["providers"]["codex"]["status"] == "not_installed"
    assert missing["providers"]["claude"]["status"] == "not_installed"


def test_local_agent_requires_token_and_uses_private_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FRAMEFETCH_AGENT_STATE_DIR", str(tmp_path))
    agent = _load_agent_module()
    status = agent.ensure_agent(AGENT_SCRIPT)
    endpoint = agent.read_endpoint()
    assert endpoint is not None

    try:
        assert status["agent"]["transport"] == "loopback_http"
        assert endpoint["baseUrl"].startswith("http://127.0.0.1:")
        if os.name != "nt":
            assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
            assert stat.S_IMODE((tmp_path / "endpoint.json").stat().st_mode) == 0o600

        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(f"{endpoint['baseUrl']}/v1/status", timeout=1)
        assert error.value.code == 401
    finally:
        agent.request_agent("POST", "/v1/stop", endpoint=endpoint)
        deadline = time.monotonic() + 3
        while agent.probe_agent(endpoint) is not None and time.monotonic() < deadline:
            time.sleep(0.05)


def test_mcp_initialization_starts_agent_and_exposes_lifecycle_tools(
    tmp_path: Path,
) -> None:
    environment = {**os.environ, "FRAMEFETCH_AGENT_STATE_DIR": str(tmp_path)}
    process = subprocess.Popen(
        [sys.executable, str(MCP_SCRIPT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert process.stdin is not None
    assert process.stdout is not None

    def request(
        identifier: int, method: str, params: dict[str, object]
    ) -> dict[str, object]:
        process.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "method": method,
                    "params": params,
                }
            )
            + "\n"
        )
        process.stdin.flush()
        return json.loads(process.stdout.readline())

    try:
        initialized = request(
            1,
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}},
        )
        listed = request(2, "tools/list", {})
        called = request(
            3,
            "tools/call",
            {"name": "framefetch_agent_status", "arguments": {}},
        )
        stopped = request(
            4,
            "tools/call",
            {"name": "framefetch_agent_stop", "arguments": {}},
        )

        assert initialized["result"]["serverInfo"]["name"] == "framefetch"
        assert {tool["name"] for tool in listed["result"]["tools"]} == {
            "framefetch_agent_status",
            "framefetch_agent_doctor",
            "framefetch_agent_start",
            "framefetch_agent_stop",
        }
        assert called["result"]["structuredContent"]["agent"]["apiVersion"] == "v1"
        assert stopped["result"]["structuredContent"] == {
            "stopped": True,
            "wasRunning": True,
        }
    finally:
        process.terminate()
        process.wait(timeout=3)
