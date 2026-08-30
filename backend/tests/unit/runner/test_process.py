from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
from app.runner.process import ProcessSupervisor, ProcessTimeoutError


def python_command(source: str, *args: str) -> tuple[str, ...]:
    return (sys.executable, "-c", source, *args)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError as exc:
        if os.name == "nt" and exc.winerror == 87:
            return False
        raise
    return True


async def wait_until_missing(pid: int) -> None:
    for _ in range(50):
        if not process_exists(pid):
            return
        await asyncio.sleep(0.01)
    pytest.fail(f"process {pid} was not terminated")


async def wait_for_pid(path: Path) -> int:
    for _ in range(100):
        try:
            value = path.read_text()
        except FileNotFoundError:
            pass
        else:
            if value.isdecimal():
                return int(value)
        await asyncio.sleep(0.01)
    pytest.fail(f"{path} did not contain a process id")


async def test_executes_argv_without_a_shell(tmp_path: Path) -> None:
    marker = tmp_path / "shell-owned"
    dangerous = f"; touch {marker}"
    supervisor = ProcessSupervisor(stdout_limit_bytes=1024, stderr_limit_bytes=1024)

    result = await supervisor.run(
        python_command("import sys; print(sys.argv[1])", dangerous),
        cwd=tmp_path,
        timeout_seconds=2,
    )

    assert result.returncode == 0
    assert dangerous.encode() in result.stdout
    assert not marker.exists()


async def test_captures_bounded_stdout_and_stderr(tmp_path: Path) -> None:
    supervisor = ProcessSupervisor(stdout_limit_bytes=128, stderr_limit_bytes=64)

    result = await supervisor.run(
        python_command(
            "import sys; sys.stdout.write('o'*4096); sys.stderr.write('e'*4096)"
        ),
        cwd=tmp_path,
        timeout_seconds=2,
    )

    assert len(result.stdout) == 128
    assert len(result.stderr) == 64
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True


async def test_writes_bounded_prompt_through_stdin(tmp_path: Path) -> None:
    supervisor = ProcessSupervisor(
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
    )

    result = await supervisor.run(
        python_command("import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"),
        cwd=tmp_path,
        timeout_seconds=2,
        input_bytes=b"private prompt",
    )

    assert result.returncode == 0
    assert result.stdout == b"private prompt"


async def test_timeout_terminates_entire_process_group(tmp_path: Path) -> None:
    child_pid_path = tmp_path / "child.pid"
    supervisor = ProcessSupervisor(
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
        terminate_grace_seconds=0.05,
    )
    source = (
        "import pathlib, subprocess, sys, time; "
        "child=subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)']); "
        "pathlib.Path('child.pid').write_text(str(child.pid)); time.sleep(30)"
    )

    with pytest.raises(ProcessTimeoutError):
        await supervisor.run(
            python_command(source),
            cwd=tmp_path,
            timeout_seconds=0.2,
        )

    child_pid = int(child_pid_path.read_text())
    await wait_until_missing(child_pid)


async def test_timeout_kills_child_that_ignores_term_and_closes_pipes(
    tmp_path: Path,
) -> None:
    child_pid_path = tmp_path / "stubborn.pid"
    supervisor = ProcessSupervisor(
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
        terminate_grace_seconds=0.05,
    )
    child_source = (
        "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "time.sleep(30)"
    )
    source = (
        "import pathlib, subprocess, sys, time; "
        f"child=subprocess.Popen([sys.executable, '-c', {child_source!r}], "
        "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
        "pathlib.Path('stubborn.pid').write_text(str(child.pid)); time.sleep(30)"
    )

    with pytest.raises(ProcessTimeoutError):
        await supervisor.run(
            python_command(source),
            cwd=tmp_path,
            timeout_seconds=0.2,
        )

    child_pid = int(child_pid_path.read_text())
    await wait_until_missing(child_pid)


async def test_cancellation_terminates_process(tmp_path: Path) -> None:
    pid_path = tmp_path / "runner.pid"
    supervisor = ProcessSupervisor(
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
        terminate_grace_seconds=0.05,
    )
    command = python_command(
        "import os, pathlib, time; "
        "pathlib.Path('runner.pid').write_text(str(os.getpid())); time.sleep(30)"
    )
    task = asyncio.create_task(
        supervisor.run(command, cwd=tmp_path, timeout_seconds=20)
    )
    pid = await wait_for_pid(pid_path)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    await wait_until_missing(pid)


async def test_rejects_empty_command(tmp_path: Path) -> None:
    supervisor = ProcessSupervisor()

    with pytest.raises(ValueError):
        await supervisor.run((), cwd=tmp_path, timeout_seconds=1)
