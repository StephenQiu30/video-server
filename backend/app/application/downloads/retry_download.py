from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.application.downloads.download_models import DownloadCreate, DownloadView
from app.application.downloads.errors import (
    ApplicationError,
    ApplicationErrorCode,
    PersistenceConflict,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)
from app.application.downloads.inspect_media import InspectMedia
from app.application.downloads.plans import plan_to_documents
from app.application.downloads.ports import (
    DownloadRepository,
    RequestFingerprinter,
    UrlCipher,
)
from app.application.downloads.queries import _owned_job
from app.application.downloads.validation import (
    validate_idempotency_key,
    validate_now,
    validate_owner_hash,
)
from app.application.downloads.views import download_view
from app.domain.downloads import DownloadStatus


class RetryDownload:
    """Create a new attempt resource from a terminal download's source selection."""

    def __init__(
        self,
        *,
        repository: DownloadRepository,
        inspect_media: InspectMedia,
        url_cipher: UrlCipher,
        fingerprinter: RequestFingerprinter,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
        max_attempts: int,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max attempts must be positive")
        self._repository = repository
        self._inspect_media = inspect_media
        self._url_cipher = url_cipher
        self._fingerprinter = fingerprinter
        self._now = now
        self._new_id = new_id
        self._max_attempts = max_attempts

    async def __call__(
        self,
        job_id: UUID,
        owner_hash: str,
        idempotency_key: str,
    ) -> DownloadView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        now = validate_now(self._now())
        original = await _owned_job(self._repository, job_id, owner_hash)
        retryable_statuses = {
            DownloadStatus.FAILED.value,
            DownloadStatus.CANCELLED.value,
        }
        if original.status == DownloadStatus.SUCCEEDED.value:
            try:
                artifact = await self._repository.get_artifact(job_id, owner_hash, now)
            except PersistenceNotFound:
                artifact = None
            if artifact is not None:
                raise ApplicationError(ApplicationErrorCode.INVALID_STATE)
        elif original.status not in retryable_statuses:
            raise ApplicationError(ApplicationErrorCode.INVALID_STATE)
        try:
            source = await self._repository.get_retry_source(job_id, owner_hash)
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        if source is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        try:
            url = self._url_cipher.decrypt(source.encrypted_url)
        except (TypeError, ValueError) as exc:
            raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc

        inspection_key = self._fingerprinter.fingerprint(
            "download-retry-inspection",
            str(original.id),
            idempotency_key,
        )
        inspection = await self._inspect_media(url, owner_hash, inspection_key)
        selected = next(
            (
                item
                for item in inspection.formats
                if plan_to_documents(item.plan)[0] == original.semantic_plan
            ),
            None,
        )
        if selected is None:
            raise ApplicationError(ApplicationErrorCode.FORMAT_UNAVAILABLE)

        command = DownloadCreate(
            id=self._new_id(),
            inspection_id=inspection.id,
            format_id=selected.id,
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            request_fingerprint=self._fingerprinter.fingerprint(
                "download-retry",
                str(original.id),
                original.request_fingerprint,
            ),
            semantic_plan=original.semantic_plan,
            max_attempts=self._max_attempts,
        )
        try:
            saved = await self._repository.create_job(
                command,
                now=now,
            )
        except PersistenceIdempotencyConflict as exc:
            raise ApplicationError(ApplicationErrorCode.IDEMPOTENCY_CONFLICT) from exc
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.RESOURCE_EXPIRED) from exc
        except PersistenceConflict as exc:
            raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
        return download_view(saved.job)
