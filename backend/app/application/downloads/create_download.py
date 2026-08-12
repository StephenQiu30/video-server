from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.downloads.download_models import DownloadCreate, DownloadView
from app.application.downloads.errors import (
    ApplicationError,
    ApplicationErrorCode,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)
from app.application.downloads.plans import plan_from_documents, plan_to_documents
from app.application.downloads.ports import DownloadRepository, RequestFingerprinter
from app.application.downloads.validation import (
    validate_idempotency_key,
    validate_now,
    validate_owner_hash,
)
from app.application.downloads.views import download_view


class CreateDownload:
    def __init__(
        self,
        *,
        repository: DownloadRepository,
        fingerprinter: RequestFingerprinter,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
        max_attempts: int,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max attempts must be positive")
        self._repository = repository
        self._fingerprinter = fingerprinter
        self._now = now
        self._new_id = new_id
        self._max_attempts = max_attempts

    async def __call__(
        self,
        inspection_id: UUID,
        format_id: UUID,
        owner_hash: str,
        idempotency_key: str,
    ) -> DownloadView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        now = validate_now(self._now())
        try:
            inspection = await self._repository.get_inspection(
                inspection_id, owner_hash, now
            )
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        if inspection is None or inspection.owner_hash != owner_hash:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        if now >= inspection.expires_at:
            raise ApplicationError(ApplicationErrorCode.RESOURCE_EXPIRED)
        selected = next(
            (item for item in inspection.formats if item.id == format_id), None
        )
        if selected is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        if now >= selected.expires_at:
            raise ApplicationError(ApplicationErrorCode.RESOURCE_EXPIRED)
        try:
            plan = plan_from_documents(selected.semantic_plan, selected.provider_hints)
        except (TypeError, ValueError) as exc:
            raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
        semantic, _ = plan_to_documents(plan)
        command = DownloadCreate(
            id=self._new_id(),
            inspection_id=inspection_id,
            format_id=format_id,
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            request_fingerprint=self._fingerprinter.fingerprint(
                "download",
                str(inspection_id),
                str(format_id),
                selected.plan_fingerprint,
            ),
            semantic_plan=semantic,
            max_attempts=self._max_attempts,
        )
        try:
            saved = await self._repository.create_job(command, now=now)
        except PersistenceIdempotencyConflict as exc:
            raise ApplicationError(ApplicationErrorCode.IDEMPOTENCY_CONFLICT) from exc
        except PersistenceNotFound as exc:
            # The inspection or selected format expired between the read above and
            # the atomic source re-validation inside create_job (TOCTOU window).
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        return download_view(saved.job)
