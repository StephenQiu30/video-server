from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.api.schemas.common import StrictModel
from app.application.downloads import DownloadAnalyticsView


class DownloadAnalyticsSummaryResponse(StrictModel):
    total: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    active: int = Field(ge=0)
    unique_users: int = Field(ge=0)
    downloaded_bytes: int = Field(ge=0)
    average_duration_seconds: float = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)


class DownloadAnalyticsDailyResponse(StrictModel):
    date: date
    total: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    cancelled: int = Field(ge=0)


class DownloadAnalyticsSourceResponse(StrictModel):
    source_key: str = Field(min_length=1, max_length=32)
    source_name: str = Field(min_length=1, max_length=64)
    total: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    active: int = Field(ge=0)
    unique_users: int = Field(ge=0)
    downloaded_bytes: int = Field(ge=0)
    success_rate: float = Field(ge=0, le=100)


class DownloadAnalyticsResponse(StrictModel):
    period_days: int = Field(ge=7, le=365)
    start: datetime
    end: datetime
    summary: DownloadAnalyticsSummaryResponse
    daily: list[DownloadAnalyticsDailyResponse]
    sources: list[DownloadAnalyticsSourceResponse]

    @classmethod
    def from_view(cls, view: DownloadAnalyticsView) -> DownloadAnalyticsResponse:
        return cls.model_validate(view)
