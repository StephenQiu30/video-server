from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import StrictModel
from app.api.schemas.inspections import SemanticPlanResponse
from app.application.downloads import DownloadUrl, DownloadView
from app.domain.downloads import (
    DownloadErrorCode,
    DownloadSourceKind,
    DownloadStage,
    DownloadStatus,
)


class DownloadRequest(StrictModel):
    """References an inspection and one format returned by that inspection."""

    inspection_id: UUID = Field(description="仍在有效期内的媒体解析资源 ID。")
    format_id: UUID = Field(description="解析结果中选择的语义下载格式 ID。")


class DownloadResponse(StrictModel):
    """Current state of a durable asynchronous download resource."""

    id: UUID
    inspection_id: UUID | None
    format_id: UUID | None
    source_kind: DownloadSourceKind
    source_label: str
    status: DownloadStatus
    stage: DownloadStage | None
    progress: int
    attempt: int
    version: int
    error_code: DownloadErrorCode | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    file_available: bool
    file_expires_at: datetime | None
    title: str | None
    extractor_key: str | None
    duration_seconds: int | None
    thumbnail_url: str | None
    format: SemanticPlanResponse | None

    @classmethod
    def from_view(cls, view: DownloadView) -> DownloadResponse:
        format_plan = view.format_plan
        return cls(
            id=view.id,
            inspection_id=view.inspection_id,
            format_id=view.format_id,
            source_kind=view.source_kind,
            source_label=view.source_label,
            status=view.status,
            stage=view.stage,
            progress=view.progress,
            attempt=view.attempt,
            version=view.version,
            error_code=view.error_code,
            created_at=view.created_at,
            updated_at=view.updated_at,
            finished_at=view.finished_at,
            file_available=view.file_available,
            file_expires_at=view.file_expires_at,
            title=view.title,
            extractor_key=view.extractor_key,
            duration_seconds=view.duration_seconds,
            thumbnail_url=view.thumbnail_url,
            format=(
                None
                if format_plan is None
                else SemanticPlanResponse(
                    height=format_plan.height,
                    width=format_plan.width,
                    fps_bucket=format_plan.fps_bucket,
                    dynamic_range=format_plan.dynamic_range,
                    video_codec_family=format_plan.video_codec_family,
                    audio_codec_family=format_plan.audio_codec_family,
                    audio_language=format_plan.audio_language,
                    container_preference=format_plan.container_preference,
                    compatibility_profile=format_plan.compatibility_profile,
                )
            ),
        )


class DownloadUrlResponse(StrictModel):
    """Short-lived URL for retrieving a completed download artifact."""

    url: str
    expires_at: datetime

    @classmethod
    def from_view(cls, view: DownloadUrl) -> DownloadUrlResponse:
        return cls(url=view.url, expires_at=view.expires_at)
