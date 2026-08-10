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
    AnalysisReportArtifactSnapshot,
    AnalysisReportSnapshot,
    AnalysisStoredReportFile,
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
    AnalysisReportArtifactRow,
    AnalysisResultRow,
    AnalysisRunRow,
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
            row = await session.scalar(
                select(AnalysisJobRow).where(
                    AnalysisJobRow.id == job_id,
                    AnalysisJobRow.deleted_at.is_(None),
                )
            )
            return None if row is None else analysis_job_snapshot(row)

    async def get_result(self, job_id: UUID) -> AnalysisResult | None:
        async with self._sessions() as session:
            document = await session.scalar(
                select(AnalysisResultRow.result_json)
                .where(AnalysisResultRow.job_id == job_id)
                .order_by(AnalysisResultRow.created_at.desc())
                .limit(1)
            )
            if document is None:
                return None
            return analysis_result_from_document(deepcopy(document))

    async def get_latest_report(self, job_id: UUID) -> AnalysisReportSnapshot | None:
        async with self._sessions() as session:
            report = await session.scalar(
                select(AnalysisResultRow)
                .where(AnalysisResultRow.job_id == job_id)
                .order_by(AnalysisResultRow.created_at.desc())
                .limit(1)
            )
            if report is None:
                return None
            artifacts = tuple(
                (
                    await session.scalars(
                        select(AnalysisReportArtifactRow).where(
                            AnalysisReportArtifactRow.report_id == report.id,
                            AnalysisReportArtifactRow.status == "available",
                        )
                    )
                ).all()
            )
            return AnalysisReportSnapshot(
                id=report.id,
                job_id=report.job_id,
                run_id=report.run_id,
                status=report.status,
                markdown=report.report_markdown,
                content_sha256=report.content_sha256,
                renderer_version=report.renderer_version,
                created_at=as_utc(report.created_at),
                published_at=(
                    None if report.published_at is None else as_utc(report.published_at)
                ),
                artifacts=tuple(
                    AnalysisReportArtifactSnapshot(
                        format=artifact.format,
                        object_key=artifact.object_key,
                        media_type=artifact.content_type,
                        size_bytes=artifact.size_bytes,
                        sha256=artifact.sha256,
                    )
                    for artifact in artifacts
                ),
            )

    async def get_current_report_file(
        self, job_id: UUID, report_format: str
    ) -> AnalysisStoredReportFile | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AnalysisReportArtifactRow)
                .join(
                    AnalysisJobRow,
                    AnalysisJobRow.current_report_id
                    == AnalysisReportArtifactRow.report_id,
                )
                .where(
                    AnalysisJobRow.id == job_id,
                    AnalysisJobRow.deleted_at.is_(None),
                    AnalysisReportArtifactRow.format == report_format,
                    AnalysisReportArtifactRow.status == "available",
                )
            )
            if row is None:
                return None
            return AnalysisStoredReportFile(
                object_key=row.object_key,
                media_type=row.content_type,
                size_bytes=row.size_bytes,
                sha256=row.sha256,
            )

    @staticmethod
    def requested_event(
        row: AnalysisJobRow,
        run: AnalysisRunRow,
        event_id: UUID,
        event_type: str,
        now: datetime,
    ) -> OutboxEventRow:
        return OutboxEventRow(
            id=event_id,
            aggregate_type="analysis_job",
            aggregate_id=row.id,
            event_type=event_type,
            payload={
                "job_id": str(row.id),
                "run_id": str(run.id),
                "run_no": run.run_no,
                "version": row.version,
            },
            available_at=now,
            created_at=now,
        )

    @staticmethod
    def report_requested_event(
        row: AnalysisJobRow,
        run: AnalysisRunRow,
        report_id: UUID,
        event_id: UUID,
        now: datetime,
    ) -> OutboxEventRow:
        return OutboxEventRow(
            id=event_id,
            aggregate_type="analysis_report",
            aggregate_id=report_id,
            event_type="analysis.report.publish.requested",
            payload={
                "job_id": str(row.id),
                "run_id": str(run.id),
                "report_id": str(report_id),
                "renderer_version": "analysis-report-v1",
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
    async def active_run(
        session: AsyncSession, row: AnalysisJobRow, *, for_update: bool = False
    ) -> AnalysisRunRow:
        statement = select(AnalysisRunRow).where(
            AnalysisRunRow.id == row.active_run_id,
            AnalysisRunRow.job_id == row.id,
        )
        if for_update:
            statement = statement.with_for_update()
        run = await session.scalar(statement)
        if run is None:
            raise PersistenceConflict("active analysis run is missing")
        return run

    @staticmethod
    def sync_run(row: AnalysisJobRow, run: AnalysisRunRow) -> None:
        run.status = row.status
        run.stage = row.stage
        run.stage_rank = row.stage_rank
        run.progress = row.progress
        run.attempt = row.attempt
        run.max_attempts = row.max_attempts
        run.version = row.version
        run.lease_owner = row.lease_owner
        run.lease_expires_at = row.lease_expires_at
        run.heartbeat_at = row.heartbeat_at
        run.started_at = row.started_at
        run.retry_at = row.retry_at
        run.cancel_requested_at = row.cancel_requested_at
        run.finished_at = row.finished_at
        run.error_code = row.error_code
        run.error_message = row.error_message
        run.updated_at = row.updated_at

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
