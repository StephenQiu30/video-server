from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsSummarySnapshot:
    total: int
    succeeded: int
    failed: int
    cancelled: int
    active: int
    unique_users: int
    downloaded_bytes: int
    duration_seconds: int


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsDailySnapshot:
    date: date
    total: int
    succeeded: int
    failed: int
    cancelled: int


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsSourceSnapshot:
    source_key: str
    total: int
    succeeded: int
    failed: int
    cancelled: int
    active: int
    unique_users: int
    downloaded_bytes: int


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsSnapshot:
    summary: DownloadAnalyticsSummarySnapshot
    daily: tuple[DownloadAnalyticsDailySnapshot, ...]
    sources: tuple[DownloadAnalyticsSourceSnapshot, ...]


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsSummaryView:
    total: int
    succeeded: int
    failed: int
    cancelled: int
    active: int
    unique_users: int
    downloaded_bytes: int
    average_duration_seconds: float
    success_rate: float


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsDailyView:
    date: date
    total: int
    succeeded: int
    failed: int
    cancelled: int


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsSourceView:
    source_key: str
    source_name: str
    total: int
    succeeded: int
    failed: int
    cancelled: int
    active: int
    unique_users: int
    downloaded_bytes: int
    success_rate: float


@dataclass(frozen=True, slots=True)
class DownloadAnalyticsView:
    period_days: int
    start: datetime
    end: datetime
    summary: DownloadAnalyticsSummaryView
    daily: tuple[DownloadAnalyticsDailyView, ...]
    sources: tuple[DownloadAnalyticsSourceView, ...]
