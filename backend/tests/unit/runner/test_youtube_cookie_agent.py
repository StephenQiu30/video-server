from __future__ import annotations

import plistlib
import stat
import subprocess
from pathlib import Path

import pytest
from app.runner import youtube_cookie_agent as agent


def _result(code: int) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess((), code, "", "")


def test_launchd_definition_is_strictly_on_demand(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(agent.sys, "executable", "/private/venv/bin/python")
    runtime = tmp_path / "runtime"

    document = agent._launch_agent_plist(
        runtime,
        tmp_path / "secret",
        "Default",
        "chrome-default-v1",
    )

    assert "RunAtLoad" not in document
    assert "KeepAlive" not in document
    assert document["QueueDirectories"] == [str(runtime / "requests")]
    assert document["StandardOutPath"] == "/dev/null"
    assert document["StandardErrorPath"] == "/dev/null"
    arguments = document["ProgramArguments"]
    assert arguments[:4] == [
        "/private/venv/bin/python",
        "-m",
        "app.runner.youtube_cookie_agent",
        "run",
    ]
    assert "kickstart" not in " ".join(arguments)


def test_install_bootstraps_without_starting_agent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    definition = tmp_path / "LaunchAgents" / "agent.plist"
    runtime = tmp_path / "runtime"
    secret = tmp_path / "secret"
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(agent, "PLIST_PATH", definition)
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(113))
    monkeypatch.setattr(
        agent.subprocess, "run", lambda command, **kwargs: actions.append(command)
    )

    agent.install_agent(
        runtime,
        secret,
        profile="Default",
        version="chrome-default-v1",
    )

    document = plistlib.loads(definition.read_bytes())
    assert actions == [("launchctl", "bootstrap", "gui/501", str(definition))]
    assert "RunAtLoad" not in document
    assert "KeepAlive" not in document
    assert stat.S_IMODE(runtime.stat().st_mode) == 0o711
    assert stat.S_IMODE((runtime / "requests").stat().st_mode) == 0o733
    assert stat.S_IMODE((runtime / "responses").stat().st_mode) == 0o733
    assert stat.S_IMODE(secret.stat().st_mode) == 0o700
    assert stat.S_IMODE(definition.stat().st_mode) == 0o600


def test_install_replaces_loaded_definition_without_kickstart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(agent, "PLIST_PATH", tmp_path / "agent.plist")
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(0))
    monkeypatch.setattr(
        agent.subprocess, "run", lambda command, **kwargs: actions.append(command)
    )

    agent.install_agent(
        tmp_path / "runtime",
        tmp_path / "secret",
        profile="Default",
        version="chrome-default-v1",
    )

    assert actions[0] == (
        "launchctl",
        "bootout",
        f"gui/501/{agent.SERVICE_ID}",
    )
    assert actions[1][0:2] == ("launchctl", "bootstrap")
    assert all("kickstart" not in action for action in actions)


def test_uninstall_boots_out_and_removes_only_empty_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    definition = tmp_path / "agent.plist"
    definition.write_text("definition")
    runtime = tmp_path / "runtime"
    (runtime / "requests").mkdir(parents=True)
    (runtime / "responses").mkdir()
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(agent, "PLIST_PATH", definition)
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(0))
    monkeypatch.setattr(
        agent.subprocess, "run", lambda command, **kwargs: actions.append(command)
    )

    agent.uninstall_agent(runtime)

    assert actions == [("launchctl", "bootout", f"gui/501/{agent.SERVICE_ID}")]
    assert not definition.exists()
    assert not runtime.exists()


def test_uninstall_preserves_nonempty_runtime_and_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runtime = tmp_path / "runtime"
    requests = runtime / "requests"
    requests.mkdir(parents=True)
    (runtime / "responses").mkdir()
    (requests / "pending.request").touch()
    secret = tmp_path / "secret"
    secret.mkdir()
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent, "PLIST_PATH", tmp_path / "missing.plist")
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(113))

    agent.uninstall_agent(runtime)

    assert runtime.exists()
    assert requests.exists()
    assert secret.exists()


@pytest.mark.parametrize(
    ("launchctl_code", "expected"),
    ((0, 0), (113, 4), (9, 9)),
)
def test_status_returns_stable_service_state(
    monkeypatch: pytest.MonkeyPatch, launchctl_code: int, expected: int
) -> None:
    monkeypatch.setattr(agent.sys, "platform", "darwin")
    monkeypatch.setattr(agent, "_launchctl_print", lambda: _result(launchctl_code))

    assert agent.agent_status() == expected


def test_main_run_drains_queue_with_explicit_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, Path, str, str]] = []
    refreshes: list[tuple[Path, str, str]] = []
    monkeypatch.setattr(agent.sys, "platform", "darwin")

    def refresh(secret: Path, *, profile: str, version: str) -> str:
        refreshes.append((secret, profile, version))
        return "ok"

    monkeypatch.setattr(agent, "sync_cookie_file_bounded", refresh)

    def drain(
        runtime: Path,
        secret: Path,
        *,
        profile: str,
        version: str,
        refresh: object,
    ) -> None:
        calls.append((runtime, secret, profile, version))
        assert callable(refresh)
        refresh()

    monkeypatch.setattr(agent, "drain_requests", drain)

    result = agent.main(
        (
            "run",
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--secret-root",
            str(tmp_path / "secret"),
            "--profile",
            "Default",
            "--version",
            "chrome-default-v1",
        )
    )

    assert result == 0
    assert calls == [
        (
            tmp_path / "runtime",
            tmp_path / "secret",
            "Default",
            "chrome-default-v1",
        )
    ]
    assert refreshes == [(tmp_path / "secret", "Default", "chrome-default-v1")]


def test_non_macos_commands_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent.sys, "platform", "linux")

    with pytest.raises(SystemExit, match="requires macOS"):
        agent.main(("status",))
