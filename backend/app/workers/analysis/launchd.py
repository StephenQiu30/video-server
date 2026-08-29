"""Create the launchd definition for the local analysis worker."""

from __future__ import annotations

import argparse
import os
import plistlib
from pathlib import Path


def write_launch_agent(
    *,
    project: Path,
    cli_binary: Path,
    output: Path,
    log: Path,
) -> None:
    project = project.resolve(strict=True)
    backend = project / "backend"
    python = backend / ".venv" / "bin" / "python"
    cli_binary = cli_binary.resolve(strict=True)
    search_path = (
        python.parent,
        cli_binary.parent,
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        Path("/bin"),
    )
    payload = {
        "Label": "com.stephenqiu.video.analysis-worker",
        "ProgramArguments": (
            str(python),
            "-m",
            "app.workers.analysis.main",
        ),
        "WorkingDirectory": str(backend),
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": os.pathsep.join(dict.fromkeys(map(str, search_path))),
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
    parser = argparse.ArgumentParser(description="Write the analysis LaunchAgent")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--cli-binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    arguments = parser.parse_args()
    write_launch_agent(
        project=arguments.project,
        cli_binary=arguments.cli_binary,
        output=arguments.output,
        log=arguments.log,
    )


if __name__ == "__main__":
    main()
