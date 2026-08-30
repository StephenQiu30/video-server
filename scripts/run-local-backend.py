#!/usr/bin/env python3
"""Supervise the complete backend topology as local host processes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import BinaryIO

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
LOG_ROOT = Path(tempfile.gettempdir()) / "framefetch-local-services"
SERVICES = (
    (
        "media-runner",
        "uvicorn",
        "app.runner.main:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        "19100",
        "--no-access-log",
    ),
    ("outbox", "app.workers.outbox.main"),
    ("download-worker", "app.workers.download.main"),
    ("import-worker", "app.workers.imports.main"),
    ("report-worker", "app.workers.report.main"),
    ("provider-canary", "app.workers.canary.main"),
    ("api", "app.main"),
)


def main() -> None:
    if not (REPOSITORY_ROOT / ".env").is_file():
        raise SystemExit("missing .env; copy .env.example and configure it first")
    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.runner.settings import get_runner_settings

    get_runner_settings().runner_workspace_root.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    python_bin = str(Path(sys.executable).resolve().parent)
    environment["PATH"] = python_bin + os.pathsep + environment.get("PATH", "")
    processes: list[tuple[str, subprocess.Popen[bytes], BinaryIO]] = []
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    for requested_signal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(requested_signal, request_stop)

    try:
        for service in SERVICES:
            name, *arguments = service
            command = _command(tuple(arguments))
            log = (LOG_ROOT / f"{name}.log").open("ab", buffering=0)
            process = subprocess.Popen(
                command,
                cwd=BACKEND_ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            processes.append((name, process, log))
            print(f"started {name} pid={process.pid} log={log.name}")
        while not stopping:
            for name, process, _log in processes:
                code = process.poll()
                if code is not None:
                    raise SystemExit(f"{name} exited unexpectedly with code {code}")
            time.sleep(0.25)
    finally:
        _stop(processes)


def _command(arguments: tuple[str, ...]) -> tuple[str, ...]:
    if arguments[0] == "uvicorn":
        return (sys.executable, "-m", *arguments)
    return (sys.executable, "-m", arguments[0])


def _stop(processes: list[tuple[str, subprocess.Popen[bytes], BinaryIO]]) -> None:
    for _name, process, _log in reversed(processes):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    deadline = time.monotonic() + 8
    for _name, process, _log in reversed(processes):
        remaining = max(0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    for _name, _process, log in processes:
        log.close()


if __name__ == "__main__":
    main()
