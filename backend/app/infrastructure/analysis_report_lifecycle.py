"""Report retention, deletion, and orphan-protection persistence."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.analysis_repository_base import AnalysisRepositoryBase
from app.infrastructure.database.models import (
    AnalysisReportArtifactRow,
    AnalysisResultRow,
    AnalysisRunRow,
)


@dataclass(frozen=True, slots=True)
class ReportPurgeResult:
    deleted: int
    failed: int


class AnalysisReportLifecycleRepository(AnalysisRepositoryBase):
    async def purge_report_artifacts(
        self,
        now: datetime,
        delete: Callable[[str], Awaitable[None]],
        *,
        limit: int = 50,
    ) -> ReportPurgeResult:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        deleted = failed = 0
        excluded: list[UUID] = []
        for _ in range(limit):
            async with self._sessions() as session, session.begin():
                statement = (
                    select(AnalysisReportArtifactRow)
                    .where(
                        AnalysisReportArtifactRow.deleted_at.is_(None),
                        or_(
                            AnalysisReportArtifactRow.status == "delete_pending",
                            AnalysisReportArtifactRow.expires_at <= now,
                        ),
                    )
                    .order_by(
                        AnalysisReportArtifactRow.expires_at,
                        AnalysisReportArtifactRow.id,
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if excluded:
                    statement = statement.where(
                        ~AnalysisReportArtifactRow.id.in_(excluded)
                    )
                artifact = await session.scalar(statement)
                if artifact is None:
                    break
                artifact.status = "delete_pending"
                try:
                    await delete(artifact.object_key)
                except Exception:
                    failed += 1
                    excluded.append(artifact.id)
                    continue
                artifact.status = "deleted"
                artifact.deleted_at = now
                await self._finish_report_deletion(session, artifact.report_id)
                deleted += 1
        return ReportPurgeResult(deleted, failed)

    async def expected_report_object_keys(self) -> frozenset[str]:
        async with self._sessions() as session:
            rows = (
                await session.execute(
                    select(
                        AnalysisResultRow.id,
                        AnalysisResultRow.job_id,
                        AnalysisRunRow.run_no,
                    )
                    .join(AnalysisRunRow, AnalysisRunRow.id == AnalysisResultRow.run_id)
                    .where(AnalysisResultRow.status != "deleted")
                )
            ).all()
        return frozenset(
            f"analyses/{job_id}/runs/{run_no}/reports/{report_id}/report.{suffix}"
            for report_id, job_id, run_no in rows
            for suffix in ("md", "docx")
        )

    @staticmethod
    async def _finish_report_deletion(session: AsyncSession, report_id: UUID) -> None:
        remaining = await session.scalar(
            select(func.count())
            .select_from(AnalysisReportArtifactRow)
            .where(
                AnalysisReportArtifactRow.report_id == report_id,
                AnalysisReportArtifactRow.deleted_at.is_(None),
            )
        )
        if remaining:
            return
        report = await session.get(AnalysisResultRow, report_id)
        if report is not None:
            report.status = "deleted"
