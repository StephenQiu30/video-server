from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from app.application.downloads.download_models import (
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
from app.domain.downloads import DownloadStatus


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
        self, repository: DownloadRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(self, job_id: UUID, owner_hash: str) -> DownloadView:
        job = await _owned_job(self._repository, job_id, owner_hash)
        if job.status not in {
            DownloadStatus.QUEUED.value,
            DownloadStatus.RUNNING.value,
            DownloadStatus.RETRY_WAIT.value,
        }:
            raise ApplicationError(ApplicationErrorCode.INVALID_STATE)
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

    async def __call__(self, job_id: UUID, owner_hash: str) -> DownloadUrl:
        job = await _owned_job(self._repository, job_id, owner_hash)
        if job.status != DownloadStatus.SUCCEEDED.value:
            raise ApplicationError(ApplicationErrorCode.DOWNLOAD_NOT_READY)
        now = validate_now(self._now())
        try:
            artifact = await self._repository.get_artifact(job_id, owner_hash, now)
        except PersistenceNotFound as exc:
            raise ApplicationError(ApplicationErrorCode.RESOURCE_EXPIRED) from exc
        if artifact is None or artifact.job_id != job_id:
            raise ApplicationError(ApplicationErrorCode.RESOURCE_EXPIRED)
        remaining = int((artifact.expires_at - now).total_seconds())
        if remaining <= 0:
            raise ApplicationError(ApplicationErrorCode.RESOURCE_EXPIRED)
        ttl_seconds = min(int(self._url_ttl.total_seconds()), remaining)
        title = await self._inspection_title(job, owner_hash, now)
        url = await self._storage.presigned_download(
            artifact.object_key, title=title, ttl_seconds=ttl_seconds
        )
        return DownloadUrl(url=url, expires_at=now + timedelta(seconds=ttl_seconds))

    async def _inspection_title(
        self, job: JobSnapshot, owner_hash: str, now: datetime
    ) -> str | None:
        inspection = await self._repository.get_inspection(
            job.inspection_id, owner_hash, now
        )
        return inspection.title if inspection is not None else None
