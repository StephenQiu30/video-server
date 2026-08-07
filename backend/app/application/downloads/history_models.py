from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.downloads import DownloadErrorCode, DownloadStatus


@dataclass(frozen=True, slots=True)
class DownloadHistoryItemSnapshot:
    id: UUID
    title: str
    thumbnail_url: str | None
    format_name: str
    status: str
    progress: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class DownloadHistorySummarySnapshot:
    total: int
    succeeded: int
    active: int
    failed: int


@dataclass(frozen=True, slots=True)
class DownloadHistoryPageSnapshot:
    items: tuple[DownloadHistoryItemSnapshot, ...]
    page: int
    page_size: int
    total: int
    summary: DownloadHistorySummarySnapshot


@dataclass(frozen=True, slots=True)
class DownloadHistoryItemView:
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


@dataclass(frozen=True, slots=True)
class DownloadHistorySummaryView:
    total: int
    succeeded: int
    active: int
    failed: int


@dataclass(frozen=True, slots=True)
class DownloadHistoryView:
    items: tuple[DownloadHistoryItemView, ...]
    page: int
    page_size: int
    total: int
    summary: DownloadHistorySummaryView
