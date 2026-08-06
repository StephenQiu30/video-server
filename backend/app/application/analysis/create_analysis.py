from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    PersistenceConflict,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)
from app.application.analysis.models import AnalysisCreate, AnalysisJobView
from app.application.analysis.ports import AnalysisRepository, RequestFingerprinter
from app.application.analysis.validation import (
    validate_idempotency_key,
    validate_label,
    validate_now,
    validate_owner_hash,
    validate_sha256,
)
from app.application.analysis.views import analysis_job_view


class CreateAnalysis:
    def __init__(
        self,
        *,
        repository: AnalysisRepository,
        fingerprinter: RequestFingerprinter,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
        max_attempts: int,
        schema_version: str,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max attempts must be positive")
        self._repository = repository
        self._fingerprinter = fingerprinter
        self._now = now
        self._new_id = new_id
        self._max_attempts = max_attempts
        self._schema_version = validate_label(schema_version, maximum=128)

    async def __call__(
        self,
        download_id: UUID,
        owner_hash: str,
        idempotency_key: str,
        profile: str,
        output_language: str,
    ) -> AnalysisJobView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        profile = validate_label(profile, maximum=128)
        output_language = validate_label(output_language, maximum=35)
        now = validate_now(self._now())
        try:
            artifact = await self._repository.get_artifact_for_download(download_id)
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
        if artifact is None or artifact.owner_hash != owner_hash:
            raise AnalysisApplicationError(AnalysisApplicationErrorCode.NOT_FOUND)
        if artifact.download_status != "succeeded":
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.ARTIFACT_NOT_READY
            )
        if now >= artifact.expires_at:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.RESOURCE_EXPIRED
            )
        sha256 = validate_sha256(artifact.sha256)
        fingerprint = self._fingerprinter.fingerprint(
            "analysis",
            str(artifact.id),
            sha256,
            profile,
            self._schema_version,
            output_language,
        )
        command = AnalysisCreate(
            id=self._new_id(),
            artifact_id=artifact.id,
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            input_sha256=sha256,
            profile=profile,
            schema_version=self._schema_version,
            output_language=output_language,
            max_attempts=self._max_attempts,
            outbox_event_id=self._new_id(),
            outbox_event_type="analysis.requested",
        )
        try:
            saved = await self._repository.create_job_and_enqueue(command, now=now)
        except PersistenceIdempotencyConflict as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.IDEMPOTENCY_CONFLICT
            ) from exc
        except PersistenceNotFound as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.NOT_FOUND
            ) from exc
        except PersistenceConflict as exc:
            raise AnalysisApplicationError(
                AnalysisApplicationErrorCode.ARTIFACT_NOT_READY
            ) from exc
        result = None
        if saved.job.status == "succeeded":
            result = await self._repository.get_result(saved.job.id)
            if result is None:
                raise AnalysisApplicationError(
                    AnalysisApplicationErrorCode.INTERNAL_ERROR
                )
        return analysis_job_view(saved.job, result=result)
