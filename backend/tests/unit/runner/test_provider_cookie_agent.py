from __future__ import annotations

import plistlib
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner import provider_cookie_agent as agent
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)


def _result(code: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess((), code, "", "")


def test_launchd_definition_is_on_demand_and_platform_neutral(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(agent.sys, "executable", "/private/venv/bin/python")

    document = agent._launch_agent_plist(
        tmp_path / "runtime",
        "Default",
    )

    assert "RunAtLoad" not in document
    assert "KeepAlive" not in document
    assert document["QueueDirectories"] == [
        str(tmp_path / "runtime" / provider.value / "requests")
        for provider in sorted(agent.browser_session_providers(), key=str)
    ]
    assert document["ProgramArguments"][:4] == [
        "/private/venv/bin/python",
        "-m",
        "app.runner.provider_cookie_agent",
        "run",
    ]


def test_install_prepares_only_the_encrypted_runtime_and_agent_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    definition = tmp_path / "LaunchAgents" / "agent.plist"
    runtime = tmp_path / "runtime"
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(agent, "PLIST_PATH", definition)
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(113))
    monkeypatch.setattr(
        agent.subprocess, "run", lambda command, **kwargs: actions.append(command)
    )

    agent.install_agent(runtime, profile="Default")

    document = plistlib.loads(definition.read_bytes())
    assert actions == [("launchctl", "bootstrap", "gui/501", str(definition))]
    assert "RunAtLoad" not in document
    assert stat.S_IMODE(runtime.stat().st_mode) == 0o711
    assert stat.S_IMODE(definition.stat().st_mode) == 0o600
    for provider in agent.browser_session_providers():
        provider_root = runtime / provider.value
        assert (provider_root / ".agent-installed").read_bytes() == (
            agent.AGENT_READY_PAYLOAD
        )
    arguments = document["ProgramArguments"]
    assert "--secret-root" not in arguments
    assert "--state-root" not in arguments


def test_agent_routes_each_request_to_an_in_memory_export(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[ProviderKey, str, ProviderSessionVersion]] = []

    def refresh(
        *,
        provider: ProviderKey,
        profile: str,
        version: ProviderSessionVersion,
    ) -> ProviderCookieLease:
        calls.append((provider, profile, version))
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, b"cookie")

    monkeypatch.setattr(agent, "export_provider_cookie_lease_bounded", refresh)

    def drain(
        _runtime: Path,
        expected: ProviderKey,
        callback: Callable[[ProviderKey, ProviderSessionVersion], ProviderCookieLease],
        _publish: object,
        **_kwargs: object,
    ) -> None:
        if expected is ProviderKey.INSTAGRAM:
            callback(expected, ProviderSessionVersion.BROWSER)

    monkeypatch.setattr(agent, "drain_request_batch", drain)

    agent.drain_requests(
        tmp_path / "runtime",
        profile="Default",
    )

    assert calls == [
        (
            ProviderKey.INSTAGRAM,
            "Default",
            ProviderSessionVersion.BROWSER,
        )
    ]


def test_non_macos_commands_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent.sys, "platform", "linux")

    with pytest.raises(SystemExit, match="requires macOS"):
        agent.main(("status",))
