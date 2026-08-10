from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.api.schemas.common import StrictModel
from app.application.analysis import AnalysisJobView, render_analysis_report_markdown
from app.domain.analysis import AnalysisErrorCode, AnalysisStage, AnalysisStatus


class AnalysisRequest(StrictModel):
    skill_id: str = Field(
        description="分析 Skill 的稳定标识，由分析 Skill 清单接口提供。",
        examples=["director-breakdown"],
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    output_language: str = Field(
        description="分析结果使用的 BCP 47 语言标签。",
        examples=["zh-CN"],
        min_length=2,
        max_length=35,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    )
    custom_prompt: str | None = Field(
        default=None,
        description=(
            "用户可编辑的分析要求，仅影响观察重点和表达，不能覆盖工具、"
            "安全边界或结果结构。"
        ),
        max_length=4_000,
        examples=["重点识别产品功能演示和界面切换。"],
    )

    @field_validator("custom_prompt")
    @classmethod
    def normalize_custom_prompt(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


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
    narrative_function: str
    highlight_score: int
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


class ProductionAdviceResponse(StrictModel):
    summary: str
    priority_shot_ids: tuple[str, ...]
    recommended_extensions: tuple[str, ...]


class AnalysisResultResponse(StrictModel):
    language: str
    title: str
    summary: EvidenceSummaryResponse
    media: AnalysisMediaResponse
    shot_count: int
    shots: tuple[ShotResponse, ...]
    highlights: tuple[HighlightResponse, ...]
    assets: tuple[VisualAssetResponse, ...]
    production_advice: ProductionAdviceResponse


class AnalysisResponse(StrictModel):
    id: UUID
    skill_id: str
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
    report_markdown: str | None

    @classmethod
    def from_view(cls, view: AnalysisJobView) -> AnalysisResponse:
        result = cls._public_result(view.result)
        if (view.status is AnalysisStatus.SUCCEEDED) != (result is not None):
            raise ValueError("analysis status and result are inconsistent")
        return cls(
            id=view.id,
            skill_id=view.skill_id,
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
            report_markdown=(
                render_analysis_report_markdown(view.result)
                if view.result is not None
                else None
            ),
        )

    @staticmethod
    def _public_result(
        result: object | None,
    ) -> AnalysisResultResponse | None:
        if result is None:
            return None
        return AnalysisResultResponse.model_validate(result)


class AnalysisSkillResponse(StrictModel):
    id: str
    display_name: str
    description: str
    default_prompt: str
