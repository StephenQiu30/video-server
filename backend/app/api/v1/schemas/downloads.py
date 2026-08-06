from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.api.v1.schemas.common import StrictModel
from app.application.downloads import DownloadUrl, DownloadView
from app.domain.downloads import DownloadErrorCode, DownloadStage, DownloadStatus


class DownloadRequest(StrictModel):
    inspection_id: UUID
    format_id: UUID


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
