"""Typed adapter between application ports and SQLAlchemy persistence."""

from datetime import datetime
from uuid import UUID

from app.application import downloads as application
from app.infrastructure import database
from app.infrastructure.download_mappers import (
    artifact_snapshot,
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
            ),
            now=now,
        )
        return job_result(stored)

    async def get_job(self, job_id: UUID) -> application.JobSnapshot:
        return job_snapshot(await self.repository.get_job(job_id))

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
