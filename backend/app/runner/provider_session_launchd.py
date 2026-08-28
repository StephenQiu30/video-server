"""Create the launchd definition for one local Provider Session Broker."""

from __future__ import annotations

import argparse
import os
import plistlib
from pathlib import Path


def write_launch_agent(
    *,
    project: Path,
    provider: str,
    version: str,
    interval_seconds: float,
    output: Path,
    log: Path,
) -> None:
    project = project.resolve(strict=True)
    backend = project / "backend"
    python = backend / ".venv" / "bin" / "python"
    status = project / ".provider-sessions" / provider / "status.json"
    arguments = (
        str(python),
        "-m",
        "app.runner.provider_session_broker",
        "--provider",
        provider,
        "--browser",
        "chrome",
        "--version",
        version,
        "--output-root",
        str(project / ".provider-secrets"),
        "--status-path",
        str(status),
        "--interval-seconds",
        str(interval_seconds),
    )
    payload = {
        "Label": f"com.stephenqiu.video.{provider}-session-broker",
        "ProgramArguments": arguments,
        "WorkingDirectory": str(backend),
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": os.pathsep.join((str(python.parent), "/usr/bin", "/bin")),
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "ThrottleInterval": 5,
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
    }
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with output.open("wb") as stream:
        plistlib.dump(payload, stream, sort_keys=True)
    output.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a Session Broker LaunchAgent")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--interval-seconds", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    arguments = parser.parse_args()
    write_launch_agent(
        project=arguments.project,
        provider=arguments.provider,
        version=arguments.version,
        interval_seconds=arguments.interval_seconds,
        output=arguments.output,
        log=arguments.log,
    )


if __name__ == "__main__":
    main()
