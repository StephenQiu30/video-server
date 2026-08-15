from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from contextlib import suppress
from datetime import timedelta
from typing import Any, TypeVar
from uuid import UUID

from app.domain.downloads import DownloadPlan, DownloadStage
from app.domain.providers import ProviderAccessContextRef

from .errors import LeaseInfrastructureError, LeaseLost
from .models import ArtifactDeliveryTarget
from .ports import (
    Clock,
    ExecutionRepository,
    ExecutionRunner,
    RunnerArtifactView,
    RunnerProgressView,
)

ResultT = TypeVar("ResultT")
_STAGE_RANKS = {
    DownloadStage.REVALIDATING: 1,
    DownloadStage.DOWNLOADING: 2,
    DownloadStage.REMUXING: 3,
    DownloadStage.VERIFYING: 4,
    DownloadStage.UPLOADING: 5,
}


class LeaseMonitor:
    def __init__(
        self,
        *,
        repository: ExecutionRepository,
        runner: ExecutionRunner,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        task_id: str,
        clock: Clock,
        lease_for: timedelta,
        interval: float,
    ) -> None:
        self._repository = repository
        self._runner = runner
        self._job_id = job_id
        self._worker_id = worker_id
        self._attempt = attempt
        self._task_id = task_id
        self._clock = clock
        self._lease_for = lease_for
        self._interval = interval

    async def run_download(
        self,
        url: str,
        plan: DownloadPlan,
        *,
        provider_media_id: str,
        extractor_key: str,
        access_context: ProviderAccessContextRef,
        delivery: ArtifactDeliveryTarget | None = None,
    ) -> RunnerArtifactView:
        task = asyncio.create_task(
            self._runner.download(
                self._task_id,
                url,
                plan,
                expected_provider_media_id=provider_media_id,
                expected_extractor_key=extractor_key,
                access_context=access_context,
                delivery=delivery,
            )
        )
        try:
            while True:
                if await _completed(task, self._interval):
                    return await task
                progress = await self._runner_progress()
                await self._heartbeat(progress.stage, progress.progress)
        except (LeaseLost, LeaseInfrastructureError, asyncio.CancelledError):
            await self._abort(task, drain=False)
            raise

    async def run_fixed(
        self,
        operation: Callable[[], Coroutine[Any, Any, ResultT]],
        *,
        stage: DownloadStage,
        progress: int,
        drain_on_abort: bool,
    ) -> ResultT:
        try:
            await self._heartbeat(stage, progress)
        except (LeaseLost, LeaseInfrastructureError, asyncio.CancelledError):
            await self._cancel_runner()
            raise
        task: asyncio.Task[ResultT] = asyncio.create_task(operation())
        try:
            while True:
                if await _completed(task, self._interval):
                    return await task
                await self._heartbeat(stage, progress)
        except (LeaseLost, LeaseInfrastructureError, asyncio.CancelledError):
            await self._abort(task, drain=drain_on_abort)
            raise

    async def _runner_progress(self) -> RunnerProgressView:
        try:
            return await self._runner.status(self._task_id)
        except Exception:
            return _FallbackProgress()

    async def _heartbeat(self, stage: DownloadStage, progress: int) -> None:
        try:
            owned = await self._repository.heartbeat(
                self._job_id,
                self._worker_id,
                self._attempt,
                stage=stage.value,
                stage_rank=_STAGE_RANKS[stage],
                progress=progress,
                now=self._clock(),
                lease_for=self._lease_for,
            )
        except Exception as exc:
            raise LeaseInfrastructureError from exc
        if not owned:
            raise LeaseLost

    async def _abort(self, task: asyncio.Task[ResultT], *, drain: bool) -> None:
        await self._cancel_runner()
        if drain:
            with suppress(BaseException):
                await asyncio.shield(task)
            return
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _cancel_runner(self) -> None:
        with suppress(Exception):
            await self._runner.cancel(self._task_id)


class _FallbackProgress:
    stage = DownloadStage.REVALIDATING
    progress = 0


async def _completed[TaskResult](
    task: asyncio.Task[TaskResult], interval: float
) -> bool:
    done, _ = await asyncio.wait({task}, timeout=interval)
    return bool(done)
