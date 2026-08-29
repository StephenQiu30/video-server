"""Per-user operating-system service lifecycle for the analysis Agent."""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

SERVICE_ID = "com.framefetch.analysis-agent"
WINDOWS_TASK = "FrameFetchAnalysisAgent"
BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent
SYSTEMD_SERVICE = "framefetch-analysis-agent.service"
LEGACY_MACOS_SERVICE_ID = "com.stephenqiu.video.analysis-worker"
LEGACY_STATE_DIR = PROJECT_ROOT / ".local-runtime" / "analysis-worker"
LEGACY_PID_PATH = LEGACY_STATE_DIR / "worker.pid"
LEGACY_PLIST_PATH = LEGACY_STATE_DIR / "launch-agent.plist"
LEGACY_MODULE = "app.workers.analysis.main"
STATE_RUNNING = 0
STATE_STOPPED = 3
STATE_MISSING = 4


@dataclass(frozen=True, slots=True)
class AgentPaths:
    definition: Path
    stdout: Path
    stderr: Path


def install_agent() -> None:
    paths = agent_paths()
    paths.definition.parent.mkdir(parents=True, exist_ok=True)
    paths.stdout.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        _stop_windows_task()
        paths.definition.write_text(_windows_task_xml(), encoding="utf-16")
        _run(
            (
                "schtasks",
                "/Create",
                "/TN",
                WINDOWS_TASK,
                "/XML",
                str(paths.definition),
                "/F",
            )
        )
        _run(("schtasks", "/Run", "/TN", WINDOWS_TASK))
        _wait_for_state(_windows_state, {STATE_RUNNING}, "Windows Agent", stable=2)
    elif sys.platform == "darwin":
        _migrate_legacy_macos_agent()
        _stop_macos_service(SERVICE_ID)
        paths.definition.write_bytes(plistlib.dumps(_launch_agent_plist(paths)))
        domain = f"gui/{os.getuid()}"
        _run(("launchctl", "enable", f"{domain}/{SERVICE_ID}"))
        _run(("launchctl", "bootstrap", domain, str(paths.definition)))
        _run(("launchctl", "kickstart", "-k", f"{domain}/{SERVICE_ID}"))
        _wait_for_state(_macos_state, {STATE_RUNNING}, "macOS Agent", stable=2)
    else:
        _migrate_legacy_linux_worker()
        paths.definition.write_text(_systemd_unit(paths), encoding="utf-8")
        _run(("systemctl", "--user", "daemon-reload"))
        _run(("systemctl", "--user", "enable", SYSTEMD_SERVICE))
        _run(("systemctl", "--user", "restart", SYSTEMD_SERVICE))
        _wait_for_state(_linux_active_state, {STATE_RUNNING}, "Linux Agent", stable=2)
    print(f"installed: {paths.definition}")


def uninstall_agent() -> None:
    paths = agent_paths()
    if sys.platform == "win32":
        existed = _stop_windows_task()
        if existed:
            _run(("schtasks", "/Delete", "/TN", WINDOWS_TASK, "/F"))
        _wait_for_state(_windows_state, {STATE_MISSING}, "Windows Agent removal")
    elif sys.platform == "darwin":
        _migrate_legacy_macos_agent()
        _stop_macos_service(SERVICE_ID)
        _wait_for_state(_macos_state, {STATE_MISSING}, "macOS Agent removal")
    else:
        _migrate_legacy_linux_worker()
        if _linux_load_state() != STATE_MISSING:
            _run(("systemctl", "--user", "disable", "--now", SYSTEMD_SERVICE))
            _wait_for_state(
                _linux_active_state,
                {STATE_STOPPED, STATE_MISSING},
                "Linux Agent stop",
            )
        paths.definition.unlink(missing_ok=True)
        _run(("systemctl", "--user", "daemon-reload"))
        _wait_for_state(_linux_load_state, {STATE_MISSING}, "Linux Agent removal")
    if sys.platform != "linux":
        paths.definition.unlink(missing_ok=True)
    print("uninstalled")


def agent_status() -> int:
    if sys.platform == "win32":
        result = _capture(_windows_status_command())
        _print_result(result)
        return result.returncode
    if sys.platform == "darwin":
        result = _launchctl_print(SERVICE_ID)
        _print_result(result)
        return _macos_result_state(result)
    return subprocess.run(
        ("systemctl", "--user", "status", SYSTEMD_SERVICE, "--no-pager"),
        check=False,
    ).returncode


def agent_paths() -> AgentPaths:
    if sys.platform == "win32":
        base = (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "FrameFetch"
        )
        definition = base / "analysis-agent.xml"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs" / "FrameFetch"
        definition = Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_ID}.plist"
    else:
        base = (
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
            / "framefetch"
        )
        definition = Path.home() / ".config" / "systemd" / "user" / SYSTEMD_SERVICE
    return AgentPaths(
        definition,
        base / "analysis-agent.log",
        base / "analysis-agent.error.log",
    )


def _stop_windows_task() -> bool:
    state = _windows_state()
    if state == STATE_MISSING:
        return False
    if state not in {STATE_RUNNING, STATE_STOPPED}:
        raise SystemExit(f"unable to inspect Windows Agent state (exit {state})")
    _run(_windows_stop_command())
    _wait_for_state(
        _windows_state,
        {STATE_STOPPED, STATE_MISSING},
        "Windows Agent stop",
    )
    return True


def _windows_state() -> int:
    return _capture(_windows_status_command()).returncode


def _windows_status_command() -> tuple[str, ...]:
    script = (
        "try { $tasks = @(Get-ScheduledTask -TaskPath '\\' -ErrorAction Stop | "
        f"Where-Object {{ $_.TaskName -ceq '{WINDOWS_TASK}' }}) }} "
        "catch { Write-Error $_; exit 20 }; "
        "if ($tasks.Count -eq 0) { exit 4 }; "
        "if ($tasks.Count -ne 1) { exit 20 }; "
        "Write-Output $tasks[0].State; "
        "if ($tasks[0].State -eq 'Running') { exit 0 } else { exit 3 }"
    )
    return ("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script)


def _windows_stop_command() -> tuple[str, ...]:
    script = (
        "try { $tasks = @(Get-ScheduledTask -TaskPath '\\' -ErrorAction Stop | "
        f"Where-Object {{ $_.TaskName -ceq '{WINDOWS_TASK}' }}); "
        "if ($tasks.Count -ne 1) { exit 20 }; "
        "$tasks[0] | Stop-ScheduledTask -ErrorAction Stop } "
        "catch { Write-Error $_; exit 20 }"
    )
    return ("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script)


def _stop_macos_service(
    label: str, *, validator: Callable[[str], bool] | None = None
) -> bool:
    result = _launchctl_print(label)
    if result.returncode == 113:
        return False
    if result.returncode != 0:
        raise SystemExit(f"unable to inspect macOS Agent (exit {result.returncode})")
    if validator is not None and not validator(result.stdout):
        raise SystemExit("refusing to stop an unrelated legacy macOS service")
    _run(("launchctl", "bootout", f"gui/{os.getuid()}/{label}"))
    _wait_for_state(
        lambda: _macos_service_state(label),
        {STATE_MISSING},
        f"macOS service {label} stop",
    )
    return True


def _macos_state() -> int:
    return _macos_service_state(SERVICE_ID)


def _macos_service_state(label: str) -> int:
    return _macos_result_state(_launchctl_print(label))


def _macos_result_state(result: subprocess.CompletedProcess[str]) -> int:
    if result.returncode == 113:
        return STATE_MISSING
    if result.returncode != 0:
        return result.returncode
    running = re.search(r"(?m)^\s*state = running\s*$", result.stdout)
    process = re.search(r"(?m)^\s*pid = [1-9][0-9]*\s*$", result.stdout)
    return STATE_RUNNING if running and process else STATE_STOPPED


def _launchctl_print(label: str) -> subprocess.CompletedProcess[str]:
    return _capture(("launchctl", "print", f"gui/{os.getuid()}/{label}"))


def _migrate_legacy_macos_agent() -> None:
    _stop_macos_service(LEGACY_MACOS_SERVICE_ID, validator=_legacy_macos_matches)
    _cleanup_legacy_state()


def _legacy_macos_matches(output: str) -> bool:
    python = BACKEND_ROOT / ".venv" / "bin" / "python"
    return all(
        re.search(pattern, output) is not None
        for pattern in (
            rf"(?m)^\s*program = {re.escape(str(python))}\s*$",
            rf"(?m)^\s*working directory = {re.escape(str(BACKEND_ROOT))}\s*$",
            rf"(?m)^\s*{re.escape(LEGACY_MODULE)}\s*$",
        )
    )


def _migrate_legacy_linux_worker() -> None:
    if not LEGACY_PID_PATH.is_file():
        _cleanup_legacy_state()
        return
    raw_pid = LEGACY_PID_PATH.read_text(encoding="utf-8").strip()
    if not raw_pid.isascii() or not raw_pid.isdigit() or int(raw_pid) <= 0:
        raise SystemExit("refusing to migrate malformed legacy analysis worker PID")
    pid = int(raw_pid)
    expected = (
        (str(BACKEND_ROOT / ".venv" / "bin" / "python"), "-m", LEGACY_MODULE),
        BACKEND_ROOT,
    )
    process = _legacy_linux_process(pid)
    if process is None:
        _cleanup_legacy_state()
        return
    if process != expected or _legacy_linux_process(pid) != expected:
        raise SystemExit("refusing to stop an unrelated legacy PID")
    os.kill(pid, signal.SIGTERM)
    _wait_for_state(
        lambda: (
            STATE_MISSING if _legacy_linux_process(pid) != expected else STATE_RUNNING
        ),
        {STATE_MISSING},
        "legacy Linux analysis worker stop",
    )
    _cleanup_legacy_state()


def _legacy_linux_process(pid: int) -> tuple[tuple[str, ...], Path] | None:
    process = Path("/proc") / str(pid)
    try:
        raw = (process / "cmdline").read_bytes()
        working_directory = (process / "cwd").resolve(strict=True)
    except FileNotFoundError:
        return None
    argv = tuple(
        part.decode(errors="surrogateescape") for part in raw.split(b"\0") if part
    )
    return argv, working_directory


def _cleanup_legacy_state() -> None:
    LEGACY_PID_PATH.unlink(missing_ok=True)
    LEGACY_PLIST_PATH.unlink(missing_ok=True)
    for directory in (LEGACY_STATE_DIR, LEGACY_STATE_DIR.parent):
        try:
            directory.rmdir()
        except OSError:
            pass


def _linux_active_state() -> int:
    result = _capture(("systemctl", "--user", "is-active", "--quiet", SYSTEMD_SERVICE))
    if result.returncode in {STATE_RUNNING, STATE_STOPPED, STATE_MISSING}:
        return result.returncode
    raise SystemExit(f"unable to inspect Linux Agent state (exit {result.returncode})")


def _linux_load_state() -> int:
    result = _capture(
        (
            "systemctl",
            "--user",
            "show",
            SYSTEMD_SERVICE,
            "--property=LoadState",
            "--value",
        )
    )
    if result.returncode != 0:
        raise SystemExit(
            f"unable to inspect Linux Agent definition (exit {result.returncode})"
        )
    return STATE_MISSING if result.stdout.strip() == "not-found" else STATE_STOPPED


def _wait_for_state(
    read: Callable[[], int],
    accepted: set[int],
    description: str,
    *,
    stable: int = 1,
) -> None:
    consecutive = 0
    last = -1
    for _ in range(50):
        last = read()
        consecutive = consecutive + 1 if last in accepted else 0
        if consecutive >= stable:
            return
        time.sleep(0.1)
    raise SystemExit(f"{description} did not reach the required state (last={last})")


def _python_executable() -> Path:
    executable = Path(sys.executable)
    if sys.platform == "win32":
        windowless = executable.with_name("pythonw.exe")
        if windowless.is_file():
            return windowless
    return executable


def _launch_agent_plist(paths: AgentPaths) -> dict[str, object]:
    return {
        "Label": SERVICE_ID,
        "ProgramArguments": [
            str(_python_executable()),
            "-m",
            "app.workers.analysis.agent_cli",
            "run",
        ],
        "WorkingDirectory": str(BACKEND_ROOT),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": os.environ.get("PATH", os.defpath),
        },
        "StandardOutPath": str(paths.stdout),
        "StandardErrorPath": str(paths.stderr),
    }


def _systemd_unit(paths: AgentPaths) -> str:
    return "\n".join(
        (
            "[Unit]",
            "Description=FrameFetch AI analysis agent",
            "After=network-online.target",
            "",
            "[Service]",
            "Type=simple",
            f"WorkingDirectory={BACKEND_ROOT}",
            f'ExecStart="{_python_executable()}" -m app.workers.analysis.agent_cli run',
            "Restart=always",
            "RestartSec=5",
            f"StandardOutput=append:{paths.stdout}",
            f"StandardError=append:{paths.stderr}",
            "",
            "[Install]",
            "WantedBy=default.target",
            "",
        )
    )


def _windows_task_xml() -> str:
    command = escape(str(_python_executable()))
    working = escape(str(BACKEND_ROOT))
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FrameFetch AI analysis agent</Description>
  </RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings><MultipleInstancesPolicy>StopExisting</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit><RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure><StartWhenAvailable>true</StartWhenAvailable>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>-m app.workers.analysis.agent_cli run</Arguments>
      <WorkingDirectory>{working}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""


def _capture(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    _require_command(command[0])
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _run(command: tuple[str, ...]) -> None:
    _require_command(command[0])
    subprocess.run(command, check=True)


def _require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"required command is unavailable: {command}")


def _print_result(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
