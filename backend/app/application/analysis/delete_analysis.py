from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    PersistenceNotFound,
)
from app.application.analysis.ports import AnalysisRepository
from app.application.analysis.validation import validate_owner_hash


class DeleteAnalysis:
    def __init__(
        self, repository: AnalysisRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(self, job_id: UUID, owner_hash: str) -> None:
        try:
            await self._repository.delete_job(
                job_id, validate_owner_hash(owner_hash), self._now()
            )
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
