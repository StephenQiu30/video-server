from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


def test_sigterm_reaps_the_extraction_process(tmp_path: Path) -> None:
    child_pid = tmp_path / "child.pid"
    child_source = (
        "import os,pathlib,signal,sys,time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
    )
    parent_source = (
        "import pathlib,sys; "
        "from app.runner import youtube_cookie_boundary as boundary; "
        "command=(sys.executable,'-c',sys.argv[2],sys.argv[1]); "
        "boundary._child_command=lambda *args: command; "
        "boundary.sync_cookie_file_bounded(pathlib.Path(sys.argv[3]), "
        "timeout_seconds=30, terminate_grace_seconds=0.05)"
    )
    parent = subprocess.Popen(
        (
            sys.executable,
            "-c",
            parent_source,
            str(child_pid),
            child_source,
            str(tmp_path),
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_file(child_pid)
        descendant = int(child_pid.read_text())
        os.kill(parent.pid, signal.SIGTERM)
        assert parent.wait(timeout=2) != 0
        _wait_until_missing(descendant)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)


def _wait_for_file(path: Path) -> None:
    for _ in range(200):
        if path.exists():
            return
        time.sleep(0.01)
    pytest.fail("extraction process did not start")


def _wait_until_missing(pid: int) -> None:
    for _ in range(200):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.01)
    pytest.fail(f"process {pid} was not terminated")
