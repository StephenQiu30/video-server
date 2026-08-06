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


class BlockingSupervisor:
    def __init__(self) -> None:
        self.download_started = asyncio.Event()
        self.download_cancelled = asyncio.Event()

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
        self.download_started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.download_cancelled.set()
            raise
        raise AssertionError("blocking command unexpectedly completed")


async def test_explicit_cancel_propagates_and_cleans_workspace(tmp_path: Path) -> None:
    supervisor = BlockingSupervisor()
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)
    task = asyncio.create_task(service.download(download_request()))
    await asyncio.wait_for(supervisor.download_started.wait(), timeout=1)

    status = await service.status("job_123")
    assert status.stage.value == "downloading"
    assert status.progress == 10

    first = await service.cancel("job_123")
    second = await service.cancel("job_123")

    with pytest.raises(RunnerFailure) as caught:
        await task
    assert caught.value.code == "cancelled"
    assert first == second
    assert supervisor.download_cancelled.is_set()
    assert list(tmp_path.iterdir()) == []
    with pytest.raises(RunnerFailure) as missing:
        await service.status("job_123")
    assert missing.value.status == 404


async def test_active_registry_is_bounded(tmp_path: Path) -> None:
    configured = settings(tmp_path).model_copy(update={"runner_max_active_tasks": 1})
    supervisor = BlockingSupervisor()
    service = MediaRunnerService(configured, supervisor=supervisor)
    first = asyncio.create_task(service.download(download_request()))
    await asyncio.wait_for(supervisor.download_started.wait(), timeout=1)

    second_request = download_request().model_copy(update={"task_id": "job_456"})
    with pytest.raises(RunnerFailure) as caught:
        await service.download(second_request)
    assert caught.value.code == "runner_busy"

    await service.cancel("job_123")
    with pytest.raises(RunnerFailure):
        await first
