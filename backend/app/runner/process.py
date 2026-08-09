from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    stdout_truncated: bool
    stderr_truncated: bool


class ProcessTimeoutError(TimeoutError):
    def __init__(self, result: ProcessResult) -> None:
        super().__init__("runner command exceeded its wall-clock timeout")
        self.result = result


@dataclass(frozen=True, slots=True)
class _Capture:
    data: bytes
    truncated: bool


class ProcessSupervisor:
    def __init__(
        self,
        *,
        stdout_limit_bytes: int = 64 * 1024,
        stderr_limit_bytes: int = 64 * 1024,
        terminate_grace_seconds: float = 1.0,
    ) -> None:
        if (
            stdout_limit_bytes <= 0
            or stderr_limit_bytes <= 0
            or terminate_grace_seconds <= 0
        ):
            raise ValueError("process supervisor limits must be positive")
        self._stdout_limit = stdout_limit_bytes
        self._stderr_limit = stderr_limit_bytes
        self._terminate_grace = terminate_grace_seconds

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_bytes: bytes | None = None,
    ) -> ProcessResult:
        command = _validate_command(argv)
        if timeout_seconds <= 0:
            raise ValueError("process timeout must be positive")

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=None if env is None else dict(env),
            stdin=(
                asyncio.subprocess.PIPE
                if input_bytes is not None
                else asyncio.subprocess.DEVNULL
            ),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        assert process.stdout is not None
        assert process.stderr is not None
        combined = asyncio.create_task(self._collect(process, input_bytes))
        try:
            result = await asyncio.wait_for(asyncio.shield(combined), timeout_seconds)
            if _process_group_exists(process.pid):
                await self._terminate_and_collect(process, combined)
            return result
        except TimeoutError:
            result = await self._terminate_and_collect(process, combined)
            raise ProcessTimeoutError(result) from None
        except asyncio.CancelledError:
            await asyncio.shield(self._terminate_and_collect(process, combined))
            raise

    async def _collect(
        self,
        process: asyncio.subprocess.Process,
        input_bytes: bytes | None,
    ) -> ProcessResult:
        assert process.stdout is not None
        assert process.stderr is not None
        stdout_task = asyncio.create_task(
            self._read_stream(process.stdout, self._stdout_limit)
        )
        stderr_task = asyncio.create_task(
            self._read_stream(process.stderr, self._stderr_limit)
        )
        input_task = asyncio.create_task(self._write_input(process, input_bytes))
        returncode, stdout, stderr, _ = await asyncio.gather(
            process.wait(),
            stdout_task,
            stderr_task,
            input_task,
        )
        return ProcessResult(
            returncode=returncode,
            stdout=stdout.data,
            stderr=stderr.data,
            stdout_truncated=stdout.truncated,
            stderr_truncated=stderr.truncated,
        )

    async def _read_stream(self, stream: asyncio.StreamReader, limit: int) -> _Capture:
        buffer = bytearray()
        truncated = False
        while chunk := await stream.read(64 * 1024):
            remaining = limit - len(buffer)
            if remaining > 0:
                buffer.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
        return _Capture(bytes(buffer), truncated)

    @staticmethod
    async def _write_input(
        process: asyncio.subprocess.Process,
        input_bytes: bytes | None,
    ) -> None:
        if input_bytes is None:
            return
        assert process.stdin is not None
        try:
            process.stdin.write(input_bytes)
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            process.stdin.close()
            with suppress(BrokenPipeError, ConnectionResetError):
                await process.stdin.wait_closed()

    async def _terminate_and_collect(
        self,
        process: asyncio.subprocess.Process,
        combined: asyncio.Task[ProcessResult],
    ) -> ProcessResult:
        _signal_process_group(process.pid, signal.SIGTERM)
        group_exited = await _wait_for_group_exit(
            process.pid,
            self._terminate_grace,
        )
        if not group_exited:
            _signal_process_group(process.pid, signal.SIGKILL)
        return await combined


def _signal_process_group(pid: int, action: signal.Signals) -> None:
    try:
        os.killpg(pid, action)
    except ProcessLookupError:
        return


def _process_group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


async def _wait_for_group_exit(pid: int, timeout_seconds: float) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while _process_group_exists(pid):
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return False
        await asyncio.sleep(min(0.01, remaining))
    return True


def _validate_command(argv: Sequence[str]) -> tuple[str, ...]:
    if not argv:
        raise ValueError("command cannot be empty")
    command = tuple(argv)
    if any(not isinstance(arg, str) or "\x00" in arg for arg in command):
        raise ValueError("command arguments must be NUL-free strings")
    if not command[0]:
        raise ValueError("executable cannot be empty")
    return command
