"""Typed adapter between application ports and SQLAlchemy persistence."""

from datetime import datetime
from uuid import UUID

from app.application import downloads as application
from app.infrastructure import database
from app.infrastructure.download_mappers import (
    artifact_snapshot,
    download_analytics_snapshot,
    inspection_result,
    inspection_snapshot,
    job_result,
    job_snapshot,
)


class SqlAlchemyDownloadStore:
    def __init__(self, repository: database.SqlAlchemyDownloadRepository) -> None:
        self.repository = repository

    async def save_inspection(
        self, command: application.InspectionCreate
    ) -> application.InspectionSaveResult:
        stored = await self.repository.save_inspection(
            database.InspectionCreate(
                id=command.id,
                owner_hash=command.owner_hash,
                idempotency_key=command.idempotency_key,
                request_fingerprint=command.request_fingerprint,
                url_ciphertext=command.url_ciphertext,
                url_nonce=command.url_nonce,
                url_key_id=command.url_key_id,
                extractor_key=command.extractor_key,
                provider_media_id=command.provider_media_id,
                title=command.title,
                duration_seconds=command.duration_seconds,
                metadata=dict(command.metadata),
                expires_at=command.expires_at,
                formats=tuple(
                    database.FormatCreate(
                        id=item.id,
                        display_name=item.display_name,
                        plan_fingerprint=item.plan_fingerprint,
                        semantic_plan=dict(item.semantic_plan),
                        provider_hints=dict(item.provider_hints),
                        expires_at=item.expires_at,
                    )
                    for item in command.formats
                ),
            )
        )
        return inspection_result(stored)

    async def get_inspection(
        self, inspection_id: UUID, owner_hash: str, now: datetime
    ) -> application.InspectionSnapshot:
        stored = await self.repository.get_inspection(
            inspection_id,
            owner_hash,
            now,
        )
        return inspection_snapshot(stored)

    async def create_job(
        self, command: application.DownloadCreate, *, now: datetime
    ) -> application.JobSaveResult:
        stored = await self.repository.create_job(
            database.DownloadCreate(
                id=command.id,
                inspection_id=command.inspection_id,
                format_id=command.format_id,
                owner_hash=command.owner_hash,
                idempotency_key=command.idempotency_key,
                request_fingerprint=command.request_fingerprint,
                semantic_plan=dict(command.semantic_plan),
                max_attempts=command.max_attempts,
                source_kind=command.source_kind.value,
            ),
            now=now,
        )
        return job_result(stored)

    async def get_job(self, job_id: UUID) -> application.JobSnapshot:
        return job_snapshot(await self.repository.get_job(job_id))

    async def get_download_presentation(
        self, job_id: UUID, owner_hash: str
    ) -> application.DownloadPresentationSnapshot:
        stored = await self.repository.get_download_presentation(job_id, owner_hash)
        return application.DownloadPresentationSnapshot(
            title=stored.title,
            extractor_key=stored.extractor_key,
            duration_seconds=stored.duration_seconds,
            thumbnail_available=stored.thumbnail_available,
        )

    async def get_thumbnail_source(
        self, inspection_id: UUID, owner_hash: str
    ) -> application.ThumbnailSource:
        stored = await self.repository.get_thumbnail_source(inspection_id, owner_hash)
        return application.ThumbnailSource(
            inspection_id=stored.inspection_id,
            owner_hash=stored.owner_hash,
            object=(
                None
                if stored.object is None
                else application.ThumbnailObject(
                    bucket=stored.object.bucket,
                    object_key=stored.object.object_key,
                    content_type=stored.object.content_type,
                    sha256=stored.object.sha256,
                    size_bytes=stored.object.size_bytes,
                )
            ),
            legacy_data_url=stored.legacy_data_url,
        )

    async def save_thumbnail(
        self,
        inspection_id: UUID,
        owner_hash: str,
        thumbnail: application.ThumbnailObject,
    ) -> None:
        await self.repository.save_thumbnail(
            inspection_id,
            owner_hash,
            database.ThumbnailSnapshot(
                bucket=thumbnail.bucket,
                object_key=thumbnail.object_key,
                content_type=thumbnail.content_type,
                sha256=thumbnail.sha256,
                size_bytes=thumbnail.size_bytes,
            ),
        )

    async def get_retry_source(
        self, job_id: UUID, owner_hash: str
    ) -> application.RetrySourceSnapshot:
        stored = await self.repository.get_retry_source(job_id, owner_hash)
        return application.RetrySourceSnapshot(
            encrypted_url=application.EncryptedUrl(
                ciphertext=stored.url_ciphertext,
                nonce=stored.url_nonce,
                key_id=stored.url_key_id,
            )
        )

    async def list_download_history(
        self,
        owner_hash: str,
        *,
        page: int,
        page_size: int,
        status: str | None,
        search: str | None,
        now: datetime,
    ) -> application.DownloadHistoryPageSnapshot:
        stored = await self.repository.list_download_history(
            owner_hash,
            page=page,
            page_size=page_size,
            status=status,
            search=search,
            now=now,
        )
        return application.DownloadHistoryPageSnapshot(
            items=tuple(
                application.DownloadHistoryItemSnapshot(
                    id=item.id,
                    inspection_id=item.inspection_id,
                    title=item.title,
                    thumbnail_available=item.thumbnail_available,
                    format_name=item.format_name,
                    status=item.status,
                    progress=item.progress,
                    error_code=item.error_code,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    finished_at=item.finished_at,
                    file_available=item.file_available,
                    source_kind=item.source_kind,
                    declared_origin=item.declared_origin,
                )
                for item in stored.items
            ),
            page=stored.page,
            page_size=stored.page_size,
            total=stored.total,
            summary=application.DownloadHistorySummarySnapshot(
                total=stored.summary.total,
                succeeded=stored.summary.succeeded,
                active=stored.summary.active,
                failed=stored.summary.failed,
            ),
        )

    async def get_download_analytics(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> application.DownloadAnalyticsSnapshot:
        stored = await self.repository.get_download_analytics(start=start, end=end)
        return download_analytics_snapshot(stored)

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> application.JobSnapshot:
        stored = await self.repository.cancel_job(job_id, owner_hash, now)
        return job_snapshot(stored)

    async def get_artifact(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> application.ArtifactSnapshot:
        stored = await self.repository.get_artifact(job_id, owner_hash, now)
        return artifact_snapshot(stored)
