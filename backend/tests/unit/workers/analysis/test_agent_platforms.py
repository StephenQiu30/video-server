from __future__ import annotations

import signal
import subprocess
from pathlib import Path

import pytest
from app.workers.analysis import agent_platforms
from app.workers.analysis.agent_platforms import AgentPaths


def _paths(tmp_path: Path) -> AgentPaths:
    return AgentPaths(
        tmp_path / "service" / "definition",
        tmp_path / "state" / "agent.log",
        tmp_path / "state" / "agent.error.log",
    )


def _result(code: int, output: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess((), code, output, "")


def test_service_definitions_are_supervised_and_single_instance() -> None:
    paths = AgentPaths(Path("definition"), Path("stdout"), Path("stderr"))
    env_file = Path("/srv/framefetch/.env.prod")

    windows = agent_platforms._windows_task_xml(env_file)
    macos = agent_platforms._launch_agent_plist(paths, env_file)
    linux = agent_platforms._systemd_unit(paths, env_file)

    assert "<MultipleInstancesPolicy>StopExisting</MultipleInstancesPolicy>" in windows
    assert "<RestartOnFailure>" in windows
    assert macos["KeepAlive"] is True
    assert macos["ProgramArguments"][-2:] == [  # type: ignore[index]
        "--env-file",
        str(env_file),
    ]
    assert "Restart=always" in linux
    assert "app.workers.analysis.agent_cli run" in linux
    assert str(env_file) in windows
    assert str(env_file) in linux


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        ("state = running\npid = 42\n", 0),
        ("state = exited\nlast exit code = 1\n", 3),
        ("state = running\n", 3),
    ),
)
def test_macos_status_requires_a_live_process(output: str, expected: int) -> None:
    assert agent_platforms._macos_result_state(_result(0, output)) == expected


def test_windows_status_distinguishes_missing_and_running() -> None:
    script = agent_platforms._windows_status_command()[-1]
    assert "Get-ScheduledTask -TaskPath '\\'" in script
    assert "tasks.Count -eq 0) { exit 4" in script
    assert "State -eq 'Running'" in script


def test_windows_install_stops_then_verifies_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    actions: list[object] = []
    monkeypatch.setattr(agent_platforms.sys, "platform", "win32")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    monkeypatch.setattr(
        agent_platforms, "_stop_windows_task", lambda: actions.append("stop")
    )
    monkeypatch.setattr(agent_platforms, "_windows_state", lambda: 0)
    monkeypatch.setattr(agent_platforms, "_run", actions.append)

    agent_platforms.install_agent()

    assert actions[0] == "stop"
    assert actions[1][0:2] == ("schtasks", "/Create")  # type: ignore[index]
    assert actions[2] == ("schtasks", "/Run", "/TN", "FrameFetchAnalysisAgent")


def test_windows_install_preserves_definition_when_stop_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    monkeypatch.setattr(agent_platforms.sys, "platform", "win32")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)

    def fail() -> bool:
        raise SystemExit("stop failed")

    monkeypatch.setattr(agent_platforms, "_stop_windows_task", fail)
    with pytest.raises(SystemExit, match="stop failed"):
        agent_platforms.install_agent()
    assert not paths.definition.exists()


def test_windows_uninstall_stops_before_delete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    paths.definition.parent.mkdir(parents=True)
    paths.definition.write_text("definition")
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent_platforms.sys, "platform", "win32")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    monkeypatch.setattr(agent_platforms, "_stop_windows_task", lambda: True)
    monkeypatch.setattr(agent_platforms, "_windows_state", lambda: 4)
    monkeypatch.setattr(agent_platforms, "_run", actions.append)

    agent_platforms.uninstall_agent()

    assert actions == [("schtasks", "/Delete", "/TN", "FrameFetchAnalysisAgent", "/F")]
    assert not paths.definition.exists()


def test_windows_uninstall_preserves_definition_when_stop_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    paths.definition.parent.mkdir(parents=True)
    paths.definition.write_text("definition")
    monkeypatch.setattr(agent_platforms.sys, "platform", "win32")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)

    def fail() -> bool:
        raise SystemExit("stop failed")

    monkeypatch.setattr(agent_platforms, "_stop_windows_task", fail)
    with pytest.raises(SystemExit, match="stop failed"):
        agent_platforms.uninstall_agent()
    assert paths.definition.is_file()


def test_macos_install_migrates_legacy_and_verifies_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    actions: list[object] = []
    monkeypatch.setattr(agent_platforms.sys, "platform", "darwin")
    monkeypatch.setattr(agent_platforms.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    monkeypatch.setattr(
        agent_platforms,
        "_migrate_legacy_macos_agent",
        lambda: actions.append("migrate"),
    )
    monkeypatch.setattr(
        agent_platforms,
        "_stop_macos_service",
        lambda label: actions.append(("stop", label)),
    )
    monkeypatch.setattr(agent_platforms, "_macos_state", lambda: 0)
    monkeypatch.setattr(agent_platforms, "_run", actions.append)

    agent_platforms.install_agent()

    assert actions[:2] == ["migrate", ("stop", agent_platforms.SERVICE_ID)]
    assert ("launchctl", "bootstrap", "gui/501", str(paths.definition)) in actions


def test_macos_legacy_migration_refuses_unrelated_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        agent_platforms,
        "_launchctl_print",
        lambda label: _result(
            0, "program = /tmp/unrelated\nstate = running\npid = 4\n"
        ),
    )
    monkeypatch.setattr(
        agent_platforms,
        "_run",
        lambda command: pytest.fail(f"must not stop: {command}"),
    )
    with pytest.raises(SystemExit, match="unrelated legacy macOS"):
        agent_platforms._migrate_legacy_macos_agent()


def test_macos_uninstall_migrates_legacy_before_canonical_stop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    paths.definition.parent.mkdir(parents=True)
    paths.definition.write_text("definition")
    actions: list[object] = []
    monkeypatch.setattr(agent_platforms.sys, "platform", "darwin")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    monkeypatch.setattr(
        agent_platforms,
        "_migrate_legacy_macos_agent",
        lambda: actions.append("migrate"),
    )
    monkeypatch.setattr(
        agent_platforms,
        "_stop_macos_service",
        lambda label: actions.append(("stop", label)),
    )
    monkeypatch.setattr(agent_platforms, "_macos_state", lambda: 4)

    agent_platforms.uninstall_agent()

    assert actions == ["migrate", ("stop", agent_platforms.SERVICE_ID)]
    assert not paths.definition.exists()


def test_linux_install_restarts_and_verifies_active(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent_platforms.sys, "platform", "linux")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    monkeypatch.setattr(agent_platforms, "_migrate_legacy_linux_worker", lambda: None)
    monkeypatch.setattr(agent_platforms, "_linux_active_state", lambda: 0)
    monkeypatch.setattr(agent_platforms, "_run", actions.append)

    agent_platforms.install_agent()

    assert actions[-1] == (
        "systemctl",
        "--user",
        "restart",
        agent_platforms.SYSTEMD_SERVICE,
    )


def test_linux_uninstall_stops_before_removing_definition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    paths.definition.parent.mkdir(parents=True)
    paths.definition.write_text("definition")
    load_states = iter((3, 4))
    actions: list[tuple[str, ...]] = []
    monkeypatch.setattr(agent_platforms.sys, "platform", "linux")
    monkeypatch.setattr(agent_platforms, "agent_paths", lambda: paths)
    migrated: list[bool] = []
    monkeypatch.setattr(
        agent_platforms,
        "_migrate_legacy_linux_worker",
        lambda: migrated.append(True),
    )
    monkeypatch.setattr(agent_platforms, "_linux_load_state", lambda: next(load_states))
    monkeypatch.setattr(agent_platforms, "_linux_active_state", lambda: 3)
    monkeypatch.setattr(agent_platforms, "_run", actions.append)

    agent_platforms.uninstall_agent()

    assert actions[0][2:4] == ("disable", "--now")
    assert migrated == [True]
    assert not paths.definition.exists()


def test_linux_legacy_migration_requires_exact_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = tmp_path / "legacy"
    pid_path = state / "worker.pid"
    state.mkdir()
    pid_path.write_text("42")
    expected = (
        (
            str(agent_platforms.BACKEND_ROOT / ".venv" / "bin" / "python"),
            "-m",
            agent_platforms.LEGACY_MODULE,
        ),
        agent_platforms.BACKEND_ROOT,
    )
    snapshots = iter((expected, expected, None))
    killed: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(agent_platforms, "LEGACY_STATE_DIR", state)
    monkeypatch.setattr(agent_platforms, "LEGACY_PID_PATH", pid_path)
    monkeypatch.setattr(agent_platforms, "LEGACY_PLIST_PATH", state / "plist")
    monkeypatch.setattr(
        agent_platforms, "_legacy_linux_process", lambda pid: next(snapshots)
    )
    monkeypatch.setattr(
        agent_platforms.os, "kill", lambda pid, sig: killed.append((pid, sig))
    )

    agent_platforms._migrate_legacy_linux_worker()

    assert killed == [(42, signal.SIGTERM)]
    assert not pid_path.exists()
