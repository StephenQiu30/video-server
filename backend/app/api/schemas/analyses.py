from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import StrictModel
from app.application.analysis import AnalysisJobView
from app.domain.analysis import AnalysisErrorCode, AnalysisStage, AnalysisStatus


class AnalysisRequest(StrictModel):
    profile: Literal["visual-shot-v1"] = Field(
        description="视觉分镜、高光与资产分析配置。",
        examples=["visual-shot-v1"],
    )
    output_language: str = Field(
        description="分析结果使用的 BCP 47 语言标签。",
        examples=["zh-CN"],
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )


class AnalysisMediaResponse(StrictModel):
    duration_ms: int
    container: str
    size_bytes: int


class EvidenceSummaryResponse(StrictModel):
    text: str
    evidence_shot_ids: tuple[str, ...]


class ShotResponse(StrictModel):
    id: str
    index: int
    start_ms: int
    end_ms: int
    representative_frame_ms: int
    description: str
    transition_in: str
    shot_size: str
    camera_motion: str
    visual_tags: tuple[str, ...]
    asset_ids: tuple[str, ...]


class HighlightResponse(StrictModel):
    id: str
    title: str
    description: str
    score: int
    reason: str
    start_ms: int
    end_ms: int
    evidence_shot_ids: tuple[str, ...]


class VisualAssetResponse(StrictModel):
    id: str
    type: str
    label: str
    description: str
    first_seen_ms: int
    evidence_shot_ids: tuple[str, ...]


class AnalysisResultResponse(StrictModel):
    language: str
    title: str
    summary: EvidenceSummaryResponse
    media: AnalysisMediaResponse
    shot_count: int
    shots: tuple[ShotResponse, ...]
    highlights: tuple[HighlightResponse, ...]
    assets: tuple[VisualAssetResponse, ...]


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
