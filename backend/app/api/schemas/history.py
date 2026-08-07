from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.api.schemas.common import StrictModel
from app.application.downloads import (
    DownloadHistoryItemView,
    DownloadHistorySummaryView,
    DownloadHistoryView,
)
from app.domain.downloads import DownloadErrorCode, DownloadStatus


class DownloadHistoryItemResponse(StrictModel):
    id: UUID
    title: str
    thumbnail_url: str | None
    format_name: str
    status: DownloadStatus
    progress: int
    error_code: DownloadErrorCode | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None

    @classmethod
    def from_view(cls, view: DownloadHistoryItemView) -> DownloadHistoryItemResponse:
        return cls.model_validate(view)


class DownloadHistorySummaryResponse(StrictModel):
    total: int
    succeeded: int
    active: int
    failed: int

    @classmethod
    def from_view(
        cls, view: DownloadHistorySummaryView
    ) -> DownloadHistorySummaryResponse:
        return cls.model_validate(view)


class DownloadHistoryResponse(StrictModel):
    items: list[DownloadHistoryItemResponse]
    page: int
    page_size: int
    total: int
    summary: DownloadHistorySummaryResponse

    @classmethod
    def from_view(cls, view: DownloadHistoryView) -> DownloadHistoryResponse:
        return cls(
            items=[DownloadHistoryItemResponse.from_view(item) for item in view.items],
            page=view.page,
            page_size=view.page_size,
            total=view.total,
            summary=DownloadHistorySummaryResponse.from_view(view.summary),
        )
