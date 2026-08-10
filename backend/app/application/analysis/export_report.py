from __future__ import annotations

from uuid import UUID

from app.application.analysis.errors import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
)
from app.application.analysis.get_analysis import GetAnalysis
from app.application.analysis.models import AnalysisReportFile
from app.application.analysis.ports import AnalysisReportRenderer
from app.application.analysis.report import render_analysis_report_markdown

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
MARKDOWN_MEDIA_TYPE = "text/markdown; charset=utf-8"


class ExportAnalysisReport:
    def __init__(
        self,
        get_analysis: GetAnalysis,
        renderer: AnalysisReportRenderer,
    ) -> None:
        self._get_analysis = get_analysis
        self._renderer = renderer

    async def __call__(self, job_id: UUID, owner_hash: str) -> AnalysisReportFile:
        view = await self._get_analysis(job_id, owner_hash)
        if view.result is None:
            raise AnalysisApplicationError(AnalysisApplicationErrorCode.INVALID_STATE)
        return AnalysisReportFile(
            content=self._renderer.render(render_analysis_report_markdown(view.result)),
            filename=f"analysis-report-{job_id}.docx",
            media_type=DOCX_MEDIA_TYPE,
        )


class ExportAnalysisMarkdown:
    def __init__(self, get_analysis: GetAnalysis) -> None:
        self._get_analysis = get_analysis

    async def __call__(self, job_id: UUID, owner_hash: str) -> AnalysisReportFile:
        view = await self._get_analysis(job_id, owner_hash)
        if view.result is None:
            raise AnalysisApplicationError(AnalysisApplicationErrorCode.INVALID_STATE)
        markdown = render_analysis_report_markdown(view.result)
        return AnalysisReportFile(
            content=markdown.encode("utf-8"),
            filename=f"analysis-report-{job_id}.md",
            media_type=MARKDOWN_MEDIA_TYPE,
        )
