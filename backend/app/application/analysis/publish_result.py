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
from app.application.analysis.models import AnalysisPublish
from app.application.analysis.ports import AnalysisRepository, Analyzer
from app.application.analysis.validation import validate_label, validate_now
from app.domain.analysis import (
    AnalysisLimits,
    AnalysisResult,
    AnalysisStage,
    AnalysisStatus,
    AnalysisValidationError,
    Transcript,
    parse_analysis_result,
)


class AnalyzeAndPublish:
    def __init__(
        self,
        *,
        repository: AnalysisRepository,
        analyzer: Analyzer,
        now: Callable[[], datetime],
        limits: AnalysisLimits | None = None,
    ) -> None:
        self._repository = repository
        self._analyzer = analyzer
        self._now = now
        self._limits = limits or AnalysisLimits()

    async def __call__(
        self, job_id: UUID, lease_owner: str, transcript: Transcript
    ) -> AnalysisResult:
        lease_owner = validate_label(lease_owner, maximum=128)
        now = validate_now(self._now())
        try:
            job = await self._repository.get_job(job_id)
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
        if job is None:
            raise AnalysisApplicationError(AnalysisApplicationErrorCode.NOT_FOUND)
        if (
            job.status != AnalysisStatus.RUNNING.value
            or job.stage != AnalysisStage.VALIDATING.value
            or job.lease_owner != lease_owner
            or job.lease_expires_at is None
            or now >= job.lease_expires_at
        ):
            raise AnalysisApplicationError(AnalysisApplicationErrorCode.INVALID_STATE)
        try:
            payload = await self._analyzer.analyze(transcript, job.output_language)
        except Exception as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.PROVIDER_FAILURE
            ) from exc
        try:
            result = parse_analysis_result(
                payload,
                transcript,
                expected_schema_version=job.schema_version,
                expected_language=job.output_language,
                limits=self._limits,
            )
        except AnalysisValidationError as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.INVALID_MODEL_OUTPUT
            ) from exc
        command = AnalysisPublish(
            job_id=job.id,
            result=result,
            lease_owner=lease_owner,
            expected_version=job.version,
            now=now,
        )
        try:
            await self._repository.publish_result(command)
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
        except PersistenceConflict as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.INVALID_STATE
            ) from exc
        return result
