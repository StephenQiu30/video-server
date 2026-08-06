from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID

from app.domain.analysis import AnalysisStage

from .errors import (
    AnalysisLeaseLost,
    AnalysisOwnershipLost,
    AnalysisPersistenceUnavailable,
)
from .ports import AnalysisExecutionRepository, AsyncOperation, Clock


class AnalysisLeaseMonitor:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        clock: Clock,
        lease_for: timedelta,
        interval: float,
    ) -> None:
        self._repository = repository
        self._job_id = job_id
        self._worker_id = worker_id
        self._attempt = attempt
        self._clock = clock
        self._lease_for = lease_for
        self._interval = interval

    async def run[ResultT](
        self,
        operation: AsyncOperation[ResultT],
        *,
        stage: AnalysisStage,
        progress: int,
    ) -> ResultT:
        await self.advance(stage, progress)
        task = asyncio.create_task(operation())
        try:
            while True:
                done, _ = await asyncio.wait({task}, timeout=self._interval)
                if done:
                    return await task
                await self.advance(stage, progress)
        except (
            AnalysisLeaseLost,
            AnalysisPersistenceUnavailable,
            asyncio.CancelledError,
        ):
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise

    async def advance(self, stage: AnalysisStage, progress: int) -> None:
        try:
            owned = await self._repository.heartbeat(
                self._job_id,
                self._worker_id,
                self._attempt,
                stage=stage.value,
                progress=progress,
                now=self._clock(),
                lease_for=self._lease_for,
            )
        except AnalysisOwnershipLost as exc:
            raise AnalysisLeaseLost from exc
        if not owned:
            raise AnalysisLeaseLost
