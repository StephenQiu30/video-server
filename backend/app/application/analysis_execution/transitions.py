from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from app.domain.analysis import AnalysisErrorCode

from .errors import (
    AnalysisOwnershipLost,
    AnalysisPersistenceUnavailable,
    AnalysisSourceUnavailable,
)
from .models import AnalysisDisposition, AnalysisExecutionSettings
from .ports import AnalysisExecutionRepository, Clock


class AnalysisTransitions:
    def __init__(
        self,
        repository: AnalysisExecutionRepository,
        settings: AnalysisExecutionSettings,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._clock = clock

    async def fail(
        self, job_id: UUID, attempt: int, code: AnalysisErrorCode
    ) -> AnalysisDisposition:
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
            return AnalysisDisposition.ACK
        except AnalysisOwnershipLost:
            return await self.converge(job_id)
        except AnalysisSourceUnavailable:
            return AnalysisDisposition.ACK
        except AnalysisPersistenceUnavailable:
            return AnalysisDisposition.REQUEUE

    async def converge(self, job_id: UUID) -> AnalysisDisposition:
        try:
            job = await self._repository.get_job(job_id)
        except AnalysisPersistenceUnavailable:
            return AnalysisDisposition.REQUEUE
        if job is None or job.status in {
            "cancelled",
            "succeeded",
            "failed",
            "retry_wait",
            "running",
        }:
            return AnalysisDisposition.ACK
        return AnalysisDisposition.REQUEUE


def _retry_delay(attempt: int) -> timedelta:
    return timedelta(seconds=min(300, 5 * (2 ** max(0, attempt - 1))))
