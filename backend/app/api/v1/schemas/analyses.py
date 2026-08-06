from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.api.v1.schemas.common import StrictModel
from app.application.analysis import AnalysisJobView
from app.domain.analysis import AnalysisErrorCode, AnalysisStage, AnalysisStatus


class AnalysisRequest(StrictModel):
    profile: Literal["standard-v1"]
    output_language: str = Field(
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )


class EvidenceStatementResponse(StrictModel):
    text: str
    evidence_segment_ids: tuple[str, ...]


class AnalysisChapterResponse(StrictModel):
    title: str
    start_ms: int
    end_ms: int
    summary: str
    evidence_segment_ids: tuple[str, ...]


class MindMapNodeResponse(StrictModel):
    id: str
    title: str
    summary: str | None
    start_ms: int | None
    evidence_segment_ids: tuple[str, ...]
    children: tuple[MindMapNodeResponse, ...]


class AnalysisResultResponse(StrictModel):
    language: str
    title: str
    summary: EvidenceStatementResponse
    key_points: tuple[EvidenceStatementResponse, ...]
    action_items: tuple[EvidenceStatementResponse, ...]
    chapters: tuple[AnalysisChapterResponse, ...]
    mind_map: MindMapNodeResponse


class _StoredAnalysisResult(AnalysisResultResponse):
    schema_version: str


class AnalysisResponse(StrictModel):
    id: UUID
    profile: str
    output_language: str
    status: AnalysisStatus
    stage: AnalysisStage | None
    progress: int
    attempt: int
    error_code: AnalysisErrorCode | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    result: AnalysisResultResponse | None

    @classmethod
    def from_view(cls, view: AnalysisJobView) -> AnalysisResponse:
        result = cls._public_result(view.result)
        if (view.status is AnalysisStatus.SUCCEEDED) != (result is not None):
            raise ValueError("analysis status and result are inconsistent")
        return cls(
            id=view.id,
            profile=view.profile,
            output_language=view.output_language,
            status=view.status,
            stage=view.stage,
            progress=view.progress,
            attempt=view.attempt,
            error_code=view.error_code,
            created_at=view.created_at,
            updated_at=view.updated_at,
            finished_at=view.finished_at,
            result=result,
        )

    @staticmethod
    def _public_result(
        document: dict[str, Any] | None,
    ) -> AnalysisResultResponse | None:
        if document is None:
            return None
        stored = _StoredAnalysisResult.model_validate(document)
        return AnalysisResultResponse.model_validate(
            stored.model_dump(exclude={"schema_version"})
        )
