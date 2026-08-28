from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from app.workers.analysis import agent_platforms
from app.workers.analysis.agent_platforms import (
    SERVICE_ID,
    AgentPaths,
    _launch_agent_plist,
    _python_executable,
    _systemd_unit,
    _windows_task_xml,
)


def _paths() -> AgentPaths:
    return AgentPaths(
        definition=Path("agent-definition"),
        stdout=Path("analysis-agent.log"),
        stderr=Path("analysis-agent.error.log"),
    )


def test_windows_task_starts_at_login_and_restarts_after_failure() -> None:
    definition = _windows_task_xml()

    assert definition.startswith('<?xml version="1.0" encoding="UTF-16"?>')
    assert "<LogonTrigger>" in definition
    assert "<RestartOnFailure>" in definition
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in definition
    assert "app.workers.analysis.agent_cli run" in definition


def test_launch_agent_starts_and_keeps_running() -> None:
    definition = _launch_agent_plist(_paths())

    assert definition["Label"] == SERVICE_ID
    assert definition["RunAtLoad"] is True
    assert definition["KeepAlive"] is True
    assert definition["WorkingDirectory"]
    assert definition["EnvironmentVariables"] == {
        "HOME": str(Path.home()),
        "PATH": agent_platforms.os.environ["PATH"],
    }
    assert definition["ProgramArguments"][-2:] == [
        "app.workers.analysis.agent_cli",
        "run",
    ]


def test_agent_keeps_virtual_environment_python_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    venv_python = "/workspace/backend/.venv/bin/python3"
    monkeypatch.setattr(agent_platforms.sys, "executable", venv_python)
    monkeypatch.setattr(agent_platforms.sys, "platform", "darwin")

    assert _python_executable() == Path(venv_python)


def test_systemd_service_starts_and_restarts_after_failure() -> None:
    definition = _systemd_unit(_paths())

    assert "WantedBy=default.target" in definition
    assert "Restart=always" in definition
    assert "RestartSec=5" in definition
    assert "app.workers.analysis.agent_cli run" in definition


@pytest.mark.parametrize(
    ("platform", "expected"),
    (
        ("win32", ("schtasks", "/Query")),
        ("darwin", ("launchctl", "print")),
        ("linux", ("systemctl", "--user")),
    ),
)
def test_status_uses_platform_service_manager(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    expected: tuple[str, str],
) -> None:
    commands: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], **kwargs: object) -> SimpleNamespace:
        del kwargs
        commands.append(command)
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(agent_platforms.sys, "platform", platform)
    if platform == "darwin":
        monkeypatch.setattr(agent_platforms.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(agent_platforms.subprocess, "run", run)

    assert agent_platforms.agent_status() == 7
    assert commands[0][:2] == expected


def test_windows_install_and_uninstall_manage_only_project_definition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = AgentPaths(
        definition=tmp_path / "FrameFetch" / "analysis-agent.xml",
        stdout=tmp_path / "FrameFetch" / "analysis-agent.log",
        stderr=tmp_path / "FrameFetch" / "analysis-agent.error.log",
    )
    checked: list[tuple[str, ...]] = []
    unchecked: list[tuple[str, ...]] = []

    monkeypatch.setattr(agent_platforms.sys, "platform", "win32")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    monkeypatch.setattr(agent_platforms, "_run", checked.append)
    monkeypatch.setattr(
        agent_platforms.subprocess,
        "run",
        lambda command, **kwargs: unchecked.append(command),
    )

    agent_platforms.install_agent()

    assert paths.definition.is_file()
    assert checked[0][:4] == ("schtasks", "/Create", "/TN", "FrameFetchAnalysisAgent")
    assert checked[1] == ("schtasks", "/Run", "/TN", "FrameFetchAnalysisAgent")

    agent_platforms.uninstall_agent()

    assert not paths.definition.exists()
    assert unchecked == [
        ("schtasks", "/Delete", "/TN", "FrameFetchAnalysisAgent", "/F")
    ]
