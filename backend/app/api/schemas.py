from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application.analysis import AnalysisJobView
from app.application.downloads import (
    DownloadUrl,
    DownloadView,
    InspectionView,
)
from app.domain.analysis import AnalysisErrorCode, AnalysisStage, AnalysisStatus
from app.domain.downloads import (
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DownloadErrorCode,
    DownloadStage,
    DownloadStatus,
    DynamicRange,
    FpsBucket,
    VideoCodecFamily,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class InspectionRequest(StrictModel):
    url: str = Field(min_length=8, max_length=4096)


class DownloadRequest(StrictModel):
    inspection_id: UUID
    format_id: UUID


class SemanticPlanResponse(StrictModel):
    height: int
    width: int
    fps_bucket: FpsBucket
    dynamic_range: DynamicRange
    video_codec_family: VideoCodecFamily
    audio_codec_family: AudioCodecFamily
    audio_language: str | None
    container_preference: ContainerPreference
    compatibility_profile: CompatibilityProfile


class FormatResponse(StrictModel):
    id: UUID
    display_name: str
    plan: SemanticPlanResponse


class InspectionResponse(StrictModel):
    id: UUID
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    expires_at: datetime
    formats: tuple[FormatResponse, ...]

    @classmethod
    def from_view(cls, view: InspectionView) -> InspectionResponse:
        return cls(
            id=view.id,
            extractor_key=view.extractor_key,
            provider_media_id=view.provider_media_id,
            title=view.title,
            duration_seconds=view.duration_seconds,
            expires_at=view.expires_at,
            formats=tuple(
                FormatResponse(
                    id=item.id,
                    display_name=item.display_name,
                    plan=SemanticPlanResponse(
                        height=item.plan.height,
                        width=item.plan.width,
                        fps_bucket=item.plan.fps_bucket,
                        dynamic_range=item.plan.dynamic_range,
                        video_codec_family=item.plan.video_codec_family,
                        audio_codec_family=item.plan.audio_codec_family,
                        audio_language=item.plan.audio_language,
                        container_preference=item.plan.container_preference,
                        compatibility_profile=item.plan.compatibility_profile,
                    ),
                )
                for item in view.formats
            ),
        )


class DownloadResponse(StrictModel):
    id: UUID
    inspection_id: UUID
    format_id: UUID
    status: DownloadStatus
    stage: DownloadStage | None
    progress: int
    attempt: int
    error_code: DownloadErrorCode | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_view(cls, view: DownloadView) -> DownloadResponse:
        return cls.model_validate(view)


class DownloadUrlResponse(StrictModel):
    url: str
    expires_at: datetime

    @classmethod
    def from_view(cls, view: DownloadUrl) -> DownloadUrlResponse:
        return cls(url=view.url, expires_at=view.expires_at)


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
