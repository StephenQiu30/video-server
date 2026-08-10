from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    PersistenceActiveRun,
    PersistenceArtifactUnavailable,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)
from app.application.analysis.models import AnalysisJobView, AnalysisRetry
from app.application.analysis.ports import AnalysisRepository
from app.application.analysis.validation import (
    validate_idempotency_key,
    validate_now,
    validate_owner_hash,
)
from app.application.analysis.views import analysis_job_view


class RetryAnalysis:
    def __init__(
        self,
        repository: AnalysisRepository,
        *,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
    ) -> None:
        self._repository = repository
        self._now = now
        self._new_id = new_id

    async def __call__(
        self, job_id: UUID, owner_hash: str, idempotency_key: str
    ) -> AnalysisJobView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        now = validate_now(self._now())
        current = await self._repository.get_job(job_id)
        if current is None or current.owner_hash != owner_hash:
            raise AnalysisApplicationError(AnalysisApplicationErrorCode.NOT_FOUND)
        command = AnalysisRetry(
            job_id=job_id,
            run_id=self._new_id(),
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            trigger=(
                "manual_rerun" if current.status == "succeeded" else "manual_retry"
            ),
            outbox_event_id=self._new_id(),
            max_attempts=current.max_attempts,
        )
        try:
            saved = await self._repository.retry_job_and_enqueue(command, now=now)
        except PersistenceActiveRun as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.ALREADY_ACTIVE
            ) from exc
        except PersistenceArtifactUnavailable as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.ARTIFACT_UNAVAILABLE
            ) from exc
        except PersistenceIdempotencyConflict as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.IDEMPOTENCY_CONFLICT
            ) from exc
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
        previous_result = await self._repository.get_result(job_id)
        return analysis_job_view(saved.job, result=previous_result)
