"""Report writers lock the aggregate before its publication to match cancellation."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import AnalysisJobRow, AnalysisResultRow


async def lock_report_and_job(
    session: AsyncSession,
    report_id: UUID,
) -> tuple[AnalysisResultRow | None, AnalysisJobRow | None]:
    job_id = await session.scalar(
        select(AnalysisResultRow.job_id).where(AnalysisResultRow.id == report_id)
    )
    if job_id is None:
        return None, None
    job = await session.scalar(
        select(AnalysisJobRow).where(AnalysisJobRow.id == job_id).with_for_update()
    )
    report = await session.scalar(
        select(AnalysisResultRow)
        .where(AnalysisResultRow.id == report_id)
        .with_for_update()
    )
    return report, job
