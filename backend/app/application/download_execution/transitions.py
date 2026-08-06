from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta
from uuid import UUID

from app.domain.downloads import DownloadErrorCode

from .errors import (
    ExecutionOwnershipLost,
    ExecutionSourceUnavailable,
)
from .models import ArtifactDetails, DownloadExecutionSettings, ExecutionDisposition
from .ports import Clock, ExecutionRepository, ExecutionStorage, JobState


class ExecutionTransitions:
    def __init__(
        self,
        repository: ExecutionRepository,
        storage: ExecutionStorage,
        settings: DownloadExecutionSettings,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._settings = settings
        self._clock = clock

    async def fail(
        self, job_id: UUID, attempt: int, code: DownloadErrorCode
    ) -> ExecutionDisposition:
        now = self._clock()
        retry_at = now + _retry_delay(attempt) if code.retryable else None
        try:
            await self._repository.complete_failure(
                job_id,
                self._settings.worker_id,
                attempt,
                error_code=code.value,
                error_message=code.value,
                retryable=code.retryable,
                now=now,
                retry_at=retry_at,
            )
            return ExecutionDisposition.ACK
        except ExecutionOwnershipLost:
            return await self.convergence(job_id)
        except Exception:
            return ExecutionDisposition.REQUEUE

    async def complete(
        self,
        job_id: UUID,
        attempt: int,
        object_key: str,
        details: ArtifactDetails,
    ) -> ExecutionDisposition:
        try:
            await self._repository.complete_success(
                job_id,
                self._settings.worker_id,
                attempt,
                details,
                now=self._clock(),
            )
            return ExecutionDisposition.ACK
        except ExecutionOwnershipLost:
            await self.delete(object_key)
            return await self.convergence(job_id)
        except Exception:
            return ExecutionDisposition.REQUEUE

    async def duplicate(self, job_id: UUID) -> ExecutionDisposition:
        try:
            job = await self._repository.get_job(job_id)
        except ExecutionSourceUnavailable:
            return ExecutionDisposition.ACK
        except Exception:
            return ExecutionDisposition.REQUEUE
        if job.status == "queued":
            return ExecutionDisposition.REQUEUE
        return ExecutionDisposition.ACK

    async def convergence(self, job_id: UUID) -> ExecutionDisposition:
        try:
            job = await self._repository.get_job(job_id)
        except ExecutionSourceUnavailable:
            return ExecutionDisposition.ACK
        except Exception:
            return ExecutionDisposition.REQUEUE
        return _converged(job, self._settings.worker_id, self._clock())

    async def delete(self, object_key: str) -> None:
        with suppress(Exception):
            await self._storage.delete(object_key)


def _retry_delay(attempt: int) -> timedelta:
    return timedelta(seconds=min(300, 5 * (2 ** max(0, attempt - 1))))


def _converged(job: JobState, worker_id: str, now: datetime) -> ExecutionDisposition:
    if job.status in {"cancelled", "succeeded", "failed", "retry_wait"}:
        return ExecutionDisposition.ACK
    if job.status == "running" and job.lease_owner != worker_id:
        return ExecutionDisposition.ACK
    return ExecutionDisposition.REQUEUE
