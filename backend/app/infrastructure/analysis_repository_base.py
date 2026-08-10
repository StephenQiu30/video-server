"""Shared reads, lease checks and safe analysis outbox construction."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from app.application.analysis import (
    AnalysisArtifactSnapshot,
    AnalysisJobSnapshot,
    PersistenceConflict,
)
from app.domain.analysis import AnalysisResult
from app.infrastructure.analysis_repository_mapping import (
    analysis_artifact_snapshot,
    analysis_job_snapshot,
)
from app.infrastructure.analysis_repository_serialization import (
    analysis_result_from_document,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    AnalysisArtifactLockRow,
    AnalysisJobRow,
    AnalysisResultRow,
    ArtifactRow,
    DownloadJobRow,
    OutboxEventRow,
)


class AnalysisRepositoryBase:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get_artifact_for_download(
        self, download_id: UUID
    ) -> AnalysisArtifactSnapshot | None:
        return await self._artifact_projection(ArtifactRow.job_id == download_id)

    async def get_artifact(self, artifact_id: UUID) -> AnalysisArtifactSnapshot | None:
        return await self._artifact_projection(ArtifactRow.id == artifact_id)

    async def _artifact_projection(
        self, criterion: ColumnElement[bool]
    ) -> AnalysisArtifactSnapshot | None:
        async with self._sessions() as session:
            result = (
                await session.execute(
                    select(ArtifactRow, DownloadJobRow)
                    .join(DownloadJobRow, DownloadJobRow.id == ArtifactRow.job_id)
                    .where(criterion, ArtifactRow.deleted_at.is_(None))
                )
            ).one_or_none()
            if result is None:
                return None
            artifact, download = result
            return analysis_artifact_snapshot(artifact, download)

    async def get_job(self, job_id: UUID) -> AnalysisJobSnapshot | None:
        async with self._sessions() as session:
            row = await session.get(AnalysisJobRow, job_id)
            return None if row is None else analysis_job_snapshot(row)

    async def get_result(self, job_id: UUID) -> AnalysisResult | None:
        async with self._sessions() as session:
            document = await session.scalar(
                select(AnalysisResultRow.result_json).where(
                    AnalysisResultRow.job_id == job_id
                )
            )
            if document is None:
                return None
            return analysis_result_from_document(deepcopy(document))

    @staticmethod
    def requested_event(
        row: AnalysisJobRow, event_id: UUID, event_type: str, now: datetime
    ) -> OutboxEventRow:
        return OutboxEventRow(
            id=event_id,
            aggregate_type="analysis_job",
            aggregate_id=row.id,
            event_type=event_type,
            payload={
                "job_id": str(row.id),
                "artifact_id": str(row.artifact_id),
                "input_sha256": row.input_sha256,
                "skill_id": row.skill_id,
                "output_language": row.output_language,
                "attempt": row.attempt,
                "version": row.version,
            },
            available_at=now,
            created_at=now,
        )

    @staticmethod
    async def release_lock(session: AsyncSession, job_id: UUID) -> None:
        await session.execute(
            delete(AnalysisArtifactLockRow).where(
                AnalysisArtifactLockRow.job_id == job_id
            )
        )

    @staticmethod
    def require_lease(
        row: AnalysisJobRow, worker_id: str, attempt: int, now: datetime
    ) -> None:
        if (
            row.status != "running"
            or row.lease_owner != worker_id
            or row.attempt != attempt
            or row.lease_expires_at is None
            or as_utc(row.lease_expires_at) <= as_utc(now)
        ):
            raise PersistenceConflict("worker no longer owns analysis attempt")
