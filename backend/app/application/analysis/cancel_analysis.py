from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.application.analysis.models import AnalysisJobView
from app.application.analysis.ports import AnalysisRepository
from app.application.analysis.validation import validate_now, validate_owner_hash
from app.application.analysis.views import analysis_job_view


class CancelAnalysis:
    def __init__(
        self,
        repository: AnalysisRepository,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(self, job_id: UUID, owner_hash: str) -> AnalysisJobView:
        owner_hash = validate_owner_hash(owner_hash)
        now = validate_now(self._now())
        try:
            snapshot = await self._repository.cancel_job(job_id, owner_hash, now)
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
        except PersistenceConflict as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.INVALID_STATE
            ) from exc
        return analysis_job_view(snapshot)
