from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StoredFileView:
    id: UUID
    category: str
    name: str
    object_count: int
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredFilePage:
    items: tuple[StoredFileView, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class StorageCleanupResult:
    older_than_days: int
    removed_resources: int
    removed_objects: int
    freed_bytes: int
    failed_resources: int
