"""Transactional report publication claims and finalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.analysis_repository_base import AnalysisRepositoryBase
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    AnalysisJobRow,
    AnalysisReportArtifactRow,
    AnalysisResultRow,
    AnalysisRunRow,
    OutboxEventRow,
)


@dataclass(frozen=True, slots=True)
class ReportPublication:
    id: UUID
    job_id: UUID
    run_id: UUID
    run_no: int
    markdown: str
    markdown_sha256: str
    renderer_version: str


@dataclass(frozen=True, slots=True)
class ReportObject:
    format: str
    bucket: str
    object_key: str
    content_type: str
    size_bytes: int
    sha256: str


class SqlAlchemyAnalysisReportRepository(AnalysisRepositoryBase):
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(sessions)

    async def claim(
        self,
        *,
        report_id: UUID,
        job_id: UUID,
        run_id: UUID,
        expected_version: int,
        worker_id: str,
        now: datetime,
        lease_for: timedelta,
    ) -> ReportPublication | None:
        async with self._sessions() as session, session.begin():
            report = await session.scalar(
                select(AnalysisResultRow)
                .where(AnalysisResultRow.id == report_id)
                .with_for_update()
            )
            if report is None or report.job_id != job_id or report.run_id != run_id:
                return None
            job = await session.get(AnalysisJobRow, job_id)
            run = await session.get(AnalysisRunRow, run_id)
            if job is None or run is None or run.job_id != job_id:
                return None
            if report.status == "available":
                return None
            if job.active_run_id != run_id or job.version != expected_version:
                return None
            if (
                report.status == "publishing"
                and report.lease_expires_at is not None
                and as_utc(report.lease_expires_at) > as_utc(now)
            ):
                return None
            report.status = "publishing"
            report.attempt += 1
            report.lease_owner = worker_id
            report.lease_expires_at = now + lease_for
            report.error_message = None
            return ReportPublication(
                id=report.id,
                job_id=job.id,
                run_id=run.id,
                run_no=run.run_no,
                markdown=report.report_markdown,
                markdown_sha256=report.content_sha256,
                renderer_version=report.renderer_version,
            )

    async def complete(
        self,
        publication: ReportPublication,
        worker_id: str,
        objects: tuple[ReportObject, ...],
        now: datetime,
    ) -> None:
        if {item.format for item in objects} != {"markdown", "docx"}:
            raise ValueError("both report formats are required")
        async with self._sessions() as session, session.begin():
            report = await session.scalar(
                select(AnalysisResultRow)
                .where(AnalysisResultRow.id == publication.id)
                .with_for_update()
            )
            if (
                report is None
                or report.status != "publishing"
                or report.lease_owner != worker_id
                or report.lease_expires_at is None
                or as_utc(report.lease_expires_at) <= as_utc(now)
            ):
                raise RuntimeError("report publication lease lost")
            existing = {
                item.format: item
                for item in (
                    await session.scalars(
                        select(AnalysisReportArtifactRow).where(
                            AnalysisReportArtifactRow.report_id == report.id
                        )
                    )
                ).all()
            }
            for item in objects:
                row = existing.get(item.format)
                if row is None:
                    session.add(
                        AnalysisReportArtifactRow(
                            id=uuid4(),
                            report_id=report.id,
                            format=item.format,
                            bucket=item.bucket,
                            object_key=item.object_key,
                            content_type=item.content_type,
                            size_bytes=item.size_bytes,
                            sha256=item.sha256,
                            status="available",
                            created_at=now,
                            available_at=now,
                        )
                    )
                elif (row.object_key, row.size_bytes, row.sha256) != (
                    item.object_key,
                    item.size_bytes,
                    item.sha256,
                ):
                    raise RuntimeError("stored report metadata conflicts")
            report.status = "available"
            report.published_at = now
            report.lease_owner = None
            report.lease_expires_at = None
            job = await session.get(AnalysisJobRow, publication.job_id)
            run = await session.get(AnalysisRunRow, publication.run_id)
            if job is not None and run is not None and job.active_run_id == run.id:
                job.current_report_id = report.id
                job.status = "succeeded"
                job.stage = None
                job.stage_rank = 0
                job.progress = 100
                job.version += 1
                job.finished_at = now
                job.updated_at = now
                self.sync_run(job, run)
                await self.release_lock(session, job.id)

    async def fail(
        self, report_id: UUID, worker_id: str, message: str, now: datetime
    ) -> None:
        async with self._sessions() as session, session.begin():
            report = await session.scalar(
                select(AnalysisResultRow)
                .where(AnalysisResultRow.id == report_id)
                .with_for_update()
            )
            if report is None or report.status == "available":
                return
            if report.lease_owner not in {None, worker_id}:
                return
            report.status = "publish_failed"
            report.error_message = message[:512]
            report.lease_owner = None
            report.lease_expires_at = None

    async def recover_pending(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]:
        async with self._sessions() as session, session.begin():
            unpublished = exists().where(
                OutboxEventRow.aggregate_type == "analysis_report",
                OutboxEventRow.aggregate_id == AnalysisResultRow.id,
                OutboxEventRow.event_type == "analysis.report.publish.requested",
                OutboxEventRow.published_at.is_(None),
            )
            reports = tuple(
                (
                    await session.scalars(
                        select(AnalysisResultRow)
                        .where(
                            or_(
                                AnalysisResultRow.status.in_(
                                    {"validated", "publish_failed"}
                                ),
                                (
                                    (AnalysisResultRow.status == "publishing")
                                    & (
                                        AnalysisResultRow.lease_expires_at.is_(None)
                                        | (AnalysisResultRow.lease_expires_at <= now)
                                    )
                                ),
                            ),
                            ~unpublished,
                        )
                        .order_by(AnalysisResultRow.created_at)
                        .limit(limit)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            recovered: list[UUID] = []
            for report in reports:
                job = await session.get(AnalysisJobRow, report.job_id)
                run = await session.get(AnalysisRunRow, report.run_id)
                if (
                    job is None
                    or run is None
                    or job.active_run_id != run.id
                    or job.stage != "publishing"
                ):
                    continue
                report.status = "publish_failed"
                report.lease_owner = None
                report.lease_expires_at = None
                session.add(
                    self.report_requested_event(job, run, report.id, uuid4(), now)
                )
                recovered.append(report.id)
            return tuple(recovered)
