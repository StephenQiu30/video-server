from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from app.runner.errors import RunnerFailure
from app.runner.process import ProcessResult
from app.runner.service import MediaRunnerService
from helpers import download_request, result, settings, split_media_info


class OversizeSupervisor:
    def __init__(self) -> None:
        self.cancelled = asyncio.Event()

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        command = tuple(argv)
        if "--dump-single-json" in command:
            return result(json.dumps(split_media_info()).encode())
        output = Path(command[command.index("--output") + 1])
        output.write_bytes(b"x" * 2048)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        raise AssertionError("oversized command unexpectedly completed")


async def test_workspace_limit_cancels_running_subprocess_and_cleans(
    tmp_path: Path,
) -> None:
    configured = settings(tmp_path).model_copy(
        update={
            "runner_max_workspace_bytes": 1024,
            "runner_workspace_poll_interval_seconds": 0.01,
        }
    )
    supervisor = OversizeSupervisor()
    service = MediaRunnerService(configured, supervisor=supervisor)

    with pytest.raises(RunnerFailure) as caught:
        await service.download(download_request())

    assert caught.value.code == "workspace_limit_exceeded"
    assert supervisor.cancelled.is_set()
    assert list(tmp_path.iterdir()) == []
