"""Per-user operating-system service definitions for the analysis Agent."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

SERVICE_ID = "com.framefetch.analysis-agent"
WINDOWS_TASK = "FrameFetchAnalysisAgent"
BACKEND_ROOT = Path(__file__).resolve().parents[3]
SYSTEMD_SERVICE = "framefetch-analysis-agent.service"


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
    elif sys.platform == "darwin":
        paths.definition.write_bytes(plistlib.dumps(_launch_agent_plist(paths)))
        domain = f"gui/{os.getuid()}"
        subprocess.run(
            ("launchctl", "bootout", domain, str(paths.definition)),
            check=False,
            capture_output=True,
        )
        _run(("launchctl", "bootstrap", domain, str(paths.definition)))
        _run(("launchctl", "kickstart", "-k", f"{domain}/{SERVICE_ID}"))
    else:
        paths.definition.write_text(_systemd_unit(paths), encoding="utf-8")
        _run(("systemctl", "--user", "daemon-reload"))
        _run(("systemctl", "--user", "enable", "--now", SYSTEMD_SERVICE))
    print(f"installed: {paths.definition}")


def uninstall_agent() -> None:
    paths = agent_paths()
    if sys.platform == "win32":
        subprocess.run(("schtasks", "/Delete", "/TN", WINDOWS_TASK, "/F"), check=False)
    elif sys.platform == "darwin":
        subprocess.run(
            ("launchctl", "bootout", f"gui/{os.getuid()}", str(paths.definition)),
            check=False,
        )
    else:
        subprocess.run(
            ("systemctl", "--user", "disable", "--now", SYSTEMD_SERVICE),
            check=False,
        )
        subprocess.run(("systemctl", "--user", "daemon-reload"), check=False)
    if paths.definition.is_file():
        paths.definition.unlink()
    print("uninstalled")


def agent_status() -> int:
    if sys.platform == "win32":
        command = ("schtasks", "/Query", "/TN", WINDOWS_TASK, "/FO", "LIST", "/V")
    elif sys.platform == "darwin":
        command = ("launchctl", "print", f"gui/{os.getuid()}/{SERVICE_ID}")
    else:
        command = (
            "systemctl",
            "--user",
            "status",
            SYSTEMD_SERVICE,
            "--no-pager",
        )
    return subprocess.run(command, check=False).returncode


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


def _python_executable() -> Path:
    executable = Path(sys.executable).resolve()
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
            "app.workers.analysis.main",
        ],
        "WorkingDirectory": str(BACKEND_ROOT),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
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
            f'ExecStart="{_python_executable()}" -m app.workers.analysis.main',
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
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval><Count>999</Count>
    </RestartOnFailure>
    <StartWhenAvailable>true</StartWhenAvailable>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>-m app.workers.analysis.main</Arguments>
      <WorkingDirectory>{working}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""


def _run(command: tuple[str, ...]) -> None:
    if shutil.which(command[0]) is None:
        raise SystemExit(f"required command is unavailable: {command[0]}")
    subprocess.run(command, check=True)
