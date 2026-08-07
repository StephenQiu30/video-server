"""Owner-scoped cancellation and artifact lookup operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from .base import as_utc
from .contracts import (
    ArtifactSnapshot,
    DownloadHistoryPageSnapshot,
    JobSnapshot,
    JobSourceSnapshot,
)
from .errors import LeaseConflict, RepositoryConflict, RepositoryNotFound
from .mapping import (
    artifact_snapshot,
    download_history_item_snapshot,
    download_history_page_snapshot,
    job_snapshot,
)
from .models import (
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
)
from .recovery_repository import RecoveryRepository


class AccessRepository(RecoveryRepository):
    async def list_download_history(
        self,
        owner_hash: str,
        *,
        page: int,
        page_size: int,
        status: str | None,
        search: str | None,
    ) -> DownloadHistoryPageSnapshot:
        filters = [DownloadJobRow.owner_hash == owner_hash]
        if status is not None:
            filters.append(DownloadJobRow.status == status)
        if search:
            filters.append(
                MediaInspectionRow.title.ilike(f"%{_escape_like(search)}%", escape="\\")
            )
        summary_filters = [DownloadJobRow.owner_hash == owner_hash]
        if search:
            summary_filters.append(
                MediaInspectionRow.title.ilike(f"%{_escape_like(search)}%", escape="\\")
            )
        offset = (page - 1) * page_size
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(DownloadJobRow, MediaInspectionRow, MediaFormatRow)
                    .join(
                        MediaInspectionRow,
                        MediaInspectionRow.id == DownloadJobRow.inspection_id,
                    )
                    .join(MediaFormatRow, MediaFormatRow.id == DownloadJobRow.format_id)
                    .where(*filters)
                    .order_by(
                        DownloadJobRow.created_at.desc(), DownloadJobRow.id.desc()
                    )
                    .offset(offset)
                    .limit(page_size)
                )
            ).all()
            total = int(
                await session.scalar(
                    select(func.count(DownloadJobRow.id))
                    .join(
                        MediaInspectionRow,
                        MediaInspectionRow.id == DownloadJobRow.inspection_id,
                    )
                    .where(*filters)
                )
                or 0
            )
            count_rows = (
                await session.execute(
                    select(DownloadJobRow.status, func.count(DownloadJobRow.id))
                    .join(
                        MediaInspectionRow,
                        MediaInspectionRow.id == DownloadJobRow.inspection_id,
                    )
                    .where(*summary_filters)
                    .group_by(DownloadJobRow.status)
                )
            ).all()
            counts: dict[str, int] = {
                status_value: int(count) for status_value, count in count_rows
            }
        items = tuple(
            download_history_item_snapshot(job, inspection, selected_format)
            for job, inspection, selected_format in rows
        )
        return download_history_page_snapshot(
            items, page=page, page_size=page_size, total=total, counts=counts
        )

    async def get_job_source(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        now: datetime,
    ) -> JobSourceSnapshot:
        async with self._sessions() as session:
            result = (
                await session.execute(
                    select(DownloadJobRow, MediaInspectionRow, MediaFormatRow)
                    .join(
                        MediaInspectionRow,
                        MediaInspectionRow.id == DownloadJobRow.inspection_id,
                    )
                    .join(MediaFormatRow, MediaFormatRow.id == DownloadJobRow.format_id)
                    .where(DownloadJobRow.id == job_id)
                )
            ).one_or_none()
            if result is None:
                raise RepositoryNotFound("download source does not exist")
            job, inspection, selected_format = result
            if (
                job.status != "running"
                or job.lease_owner != worker_id
                or job.attempt != attempt
                or job.lease_expires_at is None
                or as_utc(job.lease_expires_at) <= as_utc(now)
            ):
                raise LeaseConflict("worker no longer owns this job attempt")
            if as_utc(inspection.expires_at) <= as_utc(now):
                raise RepositoryNotFound("download source expired")
            return JobSourceSnapshot(
                job_id=job.id,
                inspection_id=inspection.id,
                semantic_plan=dict(job.semantic_plan),
                provider_hints=dict(selected_format.provider_hints),
                extractor_key=inspection.extractor_key,
                provider_media_id=inspection.provider_media_id,
                url_ciphertext=inspection.url_ciphertext,
                url_nonce=inspection.url_nonce,
                url_key_id=inspection.url_key_id,
                expires_at=as_utc(inspection.expires_at),
            )


    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> JobSnapshot:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(DownloadJobRow)
                .where(
                    DownloadJobRow.id == job_id,
                    DownloadJobRow.owner_hash == owner_hash,
                )
                .with_for_update()
            )
            if row is None:
                raise RepositoryNotFound("download job does not exist")
            if row.status == "cancelled":
                return job_snapshot(row)
            if row.status not in {"queued", "running", "retry_wait"}:
                raise RepositoryConflict("terminal download job cannot be cancelled")
            row.status = "cancelled"
            row.stage = None
            row.stage_rank = 0
            row.version += 1
            row.cancel_requested_at = now
            row.finished_at = now
            row.retry_at = None
            row.error_code = "cancelled"
            row.error_message = None
            row.lease_owner = None
            row.lease_expires_at = None
            row.updated_at = now
            await session.flush()
            return job_snapshot(row)

    async def get_artifact(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> ArtifactSnapshot:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ArtifactRow)
                .join(DownloadJobRow, DownloadJobRow.id == ArtifactRow.job_id)
                .where(
                    ArtifactRow.job_id == job_id,
                    ArtifactRow.deleted_at.is_(None),
                    ArtifactRow.expires_at > now,
                    DownloadJobRow.owner_hash == owner_hash,
                    DownloadJobRow.status == "succeeded",
                )
            )
            if row is None:
                raise RepositoryNotFound("artifact does not exist or expired")
            return artifact_snapshot(row)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
