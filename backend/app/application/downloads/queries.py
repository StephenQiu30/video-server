from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.application.downloads.download_models import (
    ArtifactSnapshot,
    DownloadUrl,
    DownloadView,
    JobSnapshot,
)
from app.application.downloads.errors import (
    ApplicationError,
    ApplicationErrorCode,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.application.downloads.inspection_models import InspectionView
from app.application.downloads.ports import DownloadRepository, ObjectStorage
from app.application.downloads.validation import validate_now, validate_owner_hash
from app.application.downloads.views import download_view, inspection_view
from app.application.imports import (
    ImportApplicationError,
    ImportApplicationErrorCode,
)
from app.domain.downloads import DownloadSourceKind, DownloadStatus


class BrowserImportCanceller(Protocol):
    async def __call__(self, resource_id: UUID, owner_hash: str) -> object: ...


async def _owned_job(
    repository: DownloadRepository, job_id: UUID, owner_hash: str
) -> JobSnapshot:
    owner_hash = validate_owner_hash(owner_hash)
    try:
        job = await repository.get_job(job_id)
    except PersistenceNotFound as exc:
        raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
    if job is None or job.owner_hash != owner_hash:
        raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
    return job


class GetDownload:
    def __init__(
        self, repository: DownloadRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(self, job_id: UUID, owner_hash: str) -> DownloadView:
        job = await _owned_job(self._repository, job_id, owner_hash)
        try:
            source_kind = DownloadSourceKind(job.source_kind)
        except ValueError as exc:
            raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
        presentation = None
        if source_kind is DownloadSourceKind.REMOTE_PROVIDER:
            presentation = await self._repository.get_download_presentation(
                job_id, validate_owner_hash(owner_hash)
            )
        artifact = None
        if job.status == DownloadStatus.SUCCEEDED.value:
            try:
                artifact = await self._repository.get_artifact(
                    job_id, owner_hash, validate_now(self._now())
                )
            except PersistenceNotFound:
                artifact = None
        return download_view(job, artifact, presentation)


class GetDownloadArtifact:
    """Authorize access to a completed artifact before it is streamed."""

    def __init__(
        self, repository: DownloadRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(self, job_id: UUID, owner_hash: str) -> ArtifactSnapshot:
        job = await _owned_job(self._repository, job_id, owner_hash)
        if job.status != DownloadStatus.SUCCEEDED.value:
            raise ApplicationError(ApplicationErrorCode.DOWNLOAD_NOT_READY)
        try:
            artifact = await self._repository.get_artifact(
                job_id, owner_hash, validate_now(self._now())
            )
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        if artifact is None or artifact.job_id != job_id:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        return artifact


class GetInspection:
    def __init__(
        self, repository: DownloadRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(self, inspection_id: UUID, owner_hash: str) -> InspectionView:
        owner_hash = validate_owner_hash(owner_hash)
        now = validate_now(self._now())
        try:
            inspection = await self._repository.get_inspection(
                inspection_id, owner_hash, now
            )
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        if inspection is None or inspection.owner_hash != owner_hash:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        if not inspection.formats:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        return inspection_view(inspection)


class CancelDownload:
    def __init__(
        self,
        repository: DownloadRepository,
        *,
        now: Callable[[], datetime],
        browser_import_canceller: BrowserImportCanceller | None = None,
    ) -> None:
        self._repository = repository
        self._now = now
        self._browser_import_canceller = browser_import_canceller

    async def __call__(self, job_id: UUID, owner_hash: str) -> DownloadView:
        job = await _owned_job(self._repository, job_id, owner_hash)
        if job.status not in {
            DownloadStatus.QUEUED.value,
            DownloadStatus.RUNNING.value,
            DownloadStatus.RETRY_WAIT.value,
        }:
            raise ApplicationError(ApplicationErrorCode.INVALID_STATE)
        try:
            source_kind = DownloadSourceKind(job.source_kind)
        except ValueError as exc:
            raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR) from exc
        if source_kind is DownloadSourceKind.BROWSER_IMPORT:
            await self._cancel_browser_import(job_id, owner_hash)
            return download_view(await _owned_job(self._repository, job_id, owner_hash))
        now = validate_now(self._now())
        try:
            cancelled = await self._repository.cancel_job(job_id, owner_hash, now)
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        except PersistenceConflict as exc:
            raise ApplicationError(ApplicationErrorCode.INVALID_STATE) from exc
        if cancelled is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        return download_view(cancelled)

    async def _cancel_browser_import(self, job_id: UUID, owner_hash: str) -> None:
        if self._browser_import_canceller is None:
            raise ApplicationError(ApplicationErrorCode.INTERNAL_ERROR)
        try:
            await self._browser_import_canceller(job_id, owner_hash)
        except ImportApplicationError as exc:
            if exc.code is ImportApplicationErrorCode.NOT_FOUND:
                code = ApplicationErrorCode.NOT_FOUND
            elif exc.code is ImportApplicationErrorCode.INVALID_STATE:
                code = ApplicationErrorCode.INVALID_STATE
            else:
                code = ApplicationErrorCode.INTERNAL_ERROR
            raise ApplicationError(code) from exc


class IssueDownloadUrl:
    def __init__(
        self,
        repository: DownloadRepository,
        storage: ObjectStorage,
        *,
        now: Callable[[], datetime],
        url_ttl: timedelta,
    ) -> None:
        if url_ttl <= timedelta(0):
            raise ValueError("download URL TTL must be positive")
        self._repository = repository
        self._storage = storage
        self._now = now
        self._url_ttl = url_ttl

    async def __call__(
        self,
        job_id: UUID,
        owner_hash: str,
        *,
        preview: bool = False,
        use_browser_proxy: bool = False,
    ) -> DownloadUrl:
        job = await _owned_job(self._repository, job_id, owner_hash)
        if job.status != DownloadStatus.SUCCEEDED.value:
            raise ApplicationError(ApplicationErrorCode.DOWNLOAD_NOT_READY)
        now = validate_now(self._now())
        try:
            artifact = await self._repository.get_artifact(job_id, owner_hash, now)
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND) from exc
        if artifact is None or artifact.job_id != job_id:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        ttl_seconds = int(self._url_ttl.total_seconds())
        title = await self._inspection_title(job, owner_hash, now)
        if use_browser_proxy:
            url = f"/api/downloads/{job_id}/file"
            if preview:
                url += "?preview=true"
        else:
            url = await self._storage.presigned_download(
                artifact.object_key,
                title=title,
                ttl_seconds=ttl_seconds,
                inline=preview,
            )
        return DownloadUrl(url=url, expires_at=now + timedelta(seconds=ttl_seconds))

    async def _inspection_title(
        self, job: JobSnapshot, owner_hash: str, now: datetime
    ) -> str | None:
        if job.inspection_id is None:
            return None
        inspection = await self._repository.get_inspection(
            job.inspection_id, owner_hash, now
        )
        return inspection.title if inspection is not None else None
