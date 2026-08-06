from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from app.runner.process import ProcessResult

ProcessStep = (
    ProcessResult | BaseException | Callable[[tuple[str, ...], Path], ProcessResult]
)


def success(stdout: bytes = b"") -> ProcessResult:
    return ProcessResult(0, stdout, b"", False, False)


def probe(duration_seconds: float, *, with_audio: bool = True) -> ProcessResult:
    streams = [{"codec_type": "audio"}] if with_audio else []
    payload = {"format": {"duration": str(duration_seconds)}, "streams": streams}
    return success(json.dumps(payload).encode())


def write_output(content: bytes) -> ProcessStep:
    def write(command: tuple[str, ...], _cwd: Path) -> ProcessResult:
        Path(command[-1]).write_bytes(content)
        return success()

    return write


class ScriptedProcessRunner:
    def __init__(self, *steps: ProcessStep) -> None:
        self.steps = list(steps)
        self.calls: list[
            tuple[tuple[str, ...], Path, float, Mapping[str, str] | None]
        ] = []

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        command = tuple(argv)
        self.calls.append((command, cwd, timeout_seconds, env))
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        if callable(step):
            return step(command, cwd)
        return step
