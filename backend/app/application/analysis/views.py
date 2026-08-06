from __future__ import annotations

from typing import Any

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
)
from app.application.analysis.models import AnalysisJobSnapshot, AnalysisJobView
from app.domain.analysis import AnalysisErrorCode, AnalysisStage, AnalysisStatus


def analysis_job_view(
    snapshot: AnalysisJobSnapshot,
    *,
    result: dict[str, Any] | None = None,
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
        profile=snapshot.profile,
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
    )
