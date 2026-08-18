from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.storage_files.ports import DeleteStoredObject
from app.infrastructure.database.models import (
    AnalysisReportArtifactRow,
    AnalysisReportVersionRow,
)


async def cleanup_reports(
    sessions: async_sessionmaker[AsyncSession],
    cutoff: datetime,
    now: datetime,
    delete: DeleteStoredObject,
) -> tuple[int, int, int, int]:
    removed = objects = freed = failed = 0
    excluded: list[UUID] = []
    while True:
        statement = (
            select(AnalysisReportVersionRow)
            .join(
                AnalysisReportArtifactRow,
                AnalysisReportArtifactRow.report_id == AnalysisReportVersionRow.id,
            )
            .where(
                AnalysisReportVersionRow.status == "available",
                AnalysisReportVersionRow.created_at < cutoff,
                AnalysisReportArtifactRow.status == "available",
                AnalysisReportArtifactRow.deleted_at.is_(None),
            )
            .order_by(AnalysisReportVersionRow.created_at, AnalysisReportVersionRow.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if excluded:
            statement = statement.where(~AnalysisReportVersionRow.id.in_(excluded))
        async with sessions() as session, session.begin():
            report = await session.scalar(statement)
            if report is None:
                break
            artifacts = tuple(
                await session.scalars(
                    select(AnalysisReportArtifactRow)
                    .where(
                        AnalysisReportArtifactRow.report_id == report.id,
                        AnalysisReportArtifactRow.status == "available",
                        AnalysisReportArtifactRow.deleted_at.is_(None),
                    )
                    .order_by(AnalysisReportArtifactRow.format)
                    .with_for_update()
                )
            )
            try:
                for artifact in artifacts:
                    await delete(artifact.object_key)
            except Exception:
                failed += 1
                excluded.append(report.id)
                continue
            report.status = "deleted"
            for artifact in artifacts:
                artifact.status = "deleted"
                artifact.deleted_at = now
            removed += 1
            objects += len(artifacts)
            freed += sum(item.size_bytes for item in artifacts)
    return removed, objects, freed, failed
