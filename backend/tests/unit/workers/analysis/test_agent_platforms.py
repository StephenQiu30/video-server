from __future__ import annotations

from pathlib import Path

from app.workers.analysis.agent_platforms import (
    SERVICE_ID,
    AgentPaths,
    _launch_agent_plist,
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
    assert "app.workers.analysis.main" in definition


def test_launch_agent_starts_and_keeps_running() -> None:
    definition = _launch_agent_plist(_paths())

    assert definition["Label"] == SERVICE_ID
    assert definition["RunAtLoad"] is True
    assert definition["KeepAlive"] is True
    assert definition["WorkingDirectory"]


def test_systemd_service_starts_and_restarts_after_failure() -> None:
    definition = _systemd_unit(_paths())

    assert "WantedBy=default.target" in definition
    assert "Restart=always" in definition
    assert "RestartSec=5" in definition
    assert "app.workers.analysis.main" in definition
