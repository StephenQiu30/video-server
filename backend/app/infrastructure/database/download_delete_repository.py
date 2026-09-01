"""Owner-scoped, storage-safe download deletion preparation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from .analytics_repository import AnalyticsRepository
from .contracts import DownloadCleanupRef, DownloadDeletionPlan
from .errors import RepositoryConflict, RepositoryNotFound
from .models import (
    AnalysisArtifactLockRow,
    ArtifactRow,
    DownloadJobRow,
    DownloadThumbnailRow,
    MediaImportAttemptRow,
)

_ACTIVE_STATUSES = {"queued", "running", "retry_wait"}


class DownloadDeleteRepository(AnalyticsRepository):
    async def prepare_download_deletion(
        self, job_id: UUID, owner_hash: str, *, now: datetime
    ) -> DownloadDeletionPlan:
        async with self._sessions() as session, session.begin():
            job = await session.scalar(
                select(DownloadJobRow)
                .where(
                    DownloadJobRow.id == job_id,
                    DownloadJobRow.owner_hash == owner_hash,
                )
                .with_for_update()
            )
            if job is None:
                raise RepositoryNotFound("download job does not exist")
            if job.status in _ACTIVE_STATUSES:
                raise RepositoryConflict("active download job must be cancelled")
            artifact = await session.scalar(
                select(ArtifactRow)
                .where(ArtifactRow.job_id == job_id)
                .with_for_update()
            )
            if artifact is not None:
                lock = await session.scalar(
                    select(AnalysisArtifactLockRow.job_id).where(
                        AnalysisArtifactLockRow.artifact_id == artifact.id
                    )
                )
                if lock is not None:
                    raise RepositoryConflict("download is locked by analysis")
                artifact.deleted_at = artifact.deleted_at or now
            thumbnail = await session.scalar(
                select(DownloadThumbnailRow)
                .where(DownloadThumbnailRow.job_id == job_id)
                .with_for_update()
            )
            attempts = tuple(
                await session.scalars(
                    select(MediaImportAttemptRow)
                    .where(MediaImportAttemptRow.resource_id == job_id)
                    .order_by(MediaImportAttemptRow.attempt)
                    .with_for_update()
                )
            )
            cleanup = tuple(
                DownloadCleanupRef(item.object_key, item.upload_id) for item in attempts
            )
            if artifact is not None:
                cleanup += (DownloadCleanupRef(artifact.object_key),)
            if thumbnail is not None:
                cleanup += (DownloadCleanupRef(thumbnail.object_key),)
            return DownloadDeletionPlan(
                job_id=job.id,
                owner_hash=job.owner_hash,
                attempt=max((job.attempt, *(item.attempt for item in attempts))),
                cleanup=cleanup,
            )

    async def finish_download_deletion(
        self, job_id: UUID, owner_hash: str
    ) -> None:
        async with self._sessions() as session, session.begin():
            job = await session.scalar(
                select(DownloadJobRow)
                .where(
                    DownloadJobRow.id == job_id,
                    DownloadJobRow.owner_hash == owner_hash,
                )
                .with_for_update()
            )
            if job is None:
                raise RepositoryNotFound("download job does not exist")
            await session.delete(job)
