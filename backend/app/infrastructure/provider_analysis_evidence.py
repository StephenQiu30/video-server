"""Read persisted full-video analysis evidence for strict validation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.provider_analysis_canary import AnalysisCanaryEvidence
from app.infrastructure.database.models import (
    AnalysisJobRow,
    AnalysisReportArtifactRow,
    AnalysisReportVersionRow,
    AnalysisRunRow,
    ArtifactRow,
    DownloadJobRow,
    MediaInspectionRow,
    TaskEventRow,
)
from app.infrastructure.provider_analysis_evidence_validation import (
    validated_evidence,
)


class SqlAlchemyAnalysisCanaryEvidenceReader:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        bucket: str,
    ) -> None:
        self._sessions = sessions
        self._bucket = bucket

    async def get(
        self, analysis_job_id: UUID, *, now: datetime
    ) -> AnalysisCanaryEvidence | None:
        async with self._sessions() as session:
            bundle = (
                await session.execute(_bundle_statement(analysis_job_id))
            ).one_or_none()
            if bundle is None:
                return None
            job, run, report, artifact, download, inspection = bundle
            report_files = tuple(
                (
                    await session.scalars(
                        select(AnalysisReportArtifactRow).where(
                            AnalysisReportArtifactRow.report_id == report.id
                        )
                    )
                ).all()
            )
            event = await session.scalar(
                select(TaskEventRow)
                .where(
                    TaskEventRow.task_type == "analysis",
                    TaskEventRow.task_id == job.id,
                )
                .order_by(TaskEventRow.version.desc())
                .limit(1)
            )
        return validated_evidence(
            job,
            run,
            report,
            artifact,
            download,
            inspection,
            report_files,
            event,
            now=now,
            bucket=self._bucket,
        )


def _bundle_statement(
    analysis_job_id: UUID,
) -> Select[
    tuple[
        AnalysisJobRow,
        AnalysisRunRow,
        AnalysisReportVersionRow,
        ArtifactRow,
        DownloadJobRow,
        MediaInspectionRow,
    ]
]:
    return (
        select(
            AnalysisJobRow,
            AnalysisRunRow,
            AnalysisReportVersionRow,
            ArtifactRow,
            DownloadJobRow,
            MediaInspectionRow,
        )
        .join(AnalysisRunRow, AnalysisRunRow.id == AnalysisJobRow.active_run_id)
        .join(
            AnalysisReportVersionRow,
            AnalysisReportVersionRow.id == AnalysisJobRow.current_report_id,
        )
        .join(ArtifactRow, ArtifactRow.id == AnalysisJobRow.artifact_id)
        .join(DownloadJobRow, DownloadJobRow.id == ArtifactRow.job_id)
        .join(MediaInspectionRow, MediaInspectionRow.id == DownloadJobRow.inspection_id)
        .where(AnalysisJobRow.id == analysis_job_id)
    )
