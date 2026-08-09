"""Primitive records returned by administrator download analytics queries."""

from dataclasses import dataclass
from datetime import date


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
