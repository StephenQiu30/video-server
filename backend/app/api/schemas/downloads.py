from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import StrictModel
from app.application.downloads import DownloadUrl, DownloadView
from app.domain.downloads import DownloadErrorCode, DownloadStage, DownloadStatus


class DownloadRequest(StrictModel):
    """References an inspection and one format returned by that inspection."""

    inspection_id: UUID = Field(description="仍在有效期内的媒体解析资源 ID。")
    format_id: UUID = Field(description="解析结果中选择的语义下载格式 ID。")


class DownloadResponse(StrictModel):
    """Current state of a durable asynchronous download resource."""

    id: UUID
    inspection_id: UUID
    format_id: UUID
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

    @classmethod
    def from_view(cls, view: DownloadView) -> DownloadResponse:
        return cls.model_validate(view)


class DownloadUrlResponse(StrictModel):
    """Short-lived URL for retrieving a completed download artifact."""

    url: str
    expires_at: datetime

    @classmethod
    def from_view(cls, view: DownloadUrl) -> DownloadUrlResponse:
        return cls(url=view.url, expires_at=view.expires_at)
