from __future__ import annotations

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
)
from app.application.analysis.models import (
    AnalysisJobSnapshot,
    AnalysisJobView,
    AnalysisReportSnapshot,
)
from app.domain.analysis import (
    AnalysisErrorCode,
    AnalysisResult,
    AnalysisStage,
    AnalysisStatus,
)


def analysis_job_view(
    snapshot: AnalysisJobSnapshot,
    *,
    result: AnalysisResult | None = None,
    report: AnalysisReportSnapshot | None = None,
) -> AnalysisJobView:
    try:
        status = AnalysisStatus(snapshot.status)
        stage = AnalysisStage(snapshot.stage) if snapshot.stage is not None else None
        error = (
            AnalysisErrorCode(snapshot.error_code)
            if snapshot.error_code is not None
            else None
        )
    except ValueError as exc:
        raise AnalysisApplicationError(
            AnalysisApplicationErrorCode.INTERNAL_ERROR
        ) from exc
    return AnalysisJobView(
        id=snapshot.id,
        run_id=snapshot.run_id,
        run_no=snapshot.run_no,
        run_trigger=snapshot.run_trigger,
        version=snapshot.version,
        skill_id=snapshot.skill_id,
        output_language=snapshot.output_language,
        status=status,
        stage=stage,
        progress=snapshot.progress,
        attempt=snapshot.attempt,
        error_code=error,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        finished_at=snapshot.finished_at,
        result=result,
        report=report,
        current_report_id=snapshot.current_report_id,
        retry_available_until=snapshot.retry_available_until,
    )
