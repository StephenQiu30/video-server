from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.downloads import DownloadErrorCode, DownloadSourceKind, DownloadStatus


@dataclass(frozen=True, slots=True)
class DownloadHistoryItemSnapshot:
    id: UUID
    inspection_id: UUID | None
    title: str
    thumbnail_available: bool
    format_name: str
    status: str
    progress: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    file_available: bool = False
    source_kind: str = DownloadSourceKind.REMOTE_PROVIDER.value


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
    file_available: bool = False
    source_kind: DownloadSourceKind = DownloadSourceKind.REMOTE_PROVIDER
    source_label: str = "链接下载"


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
