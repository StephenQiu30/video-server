"""Read the user's parse and video analysis records as one history."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.services.downloads.validation import validate_owner_hash


class HistoryRecordKind(StrEnum):
    PARSE = "parse"
    VIDEO_ANALYSIS = "video_analysis"


@dataclass(frozen=True, slots=True)
class HistoryRecordCursor:
    created_at: datetime
    record_type: HistoryRecordKind
    id: UUID


@dataclass(frozen=True, slots=True)
class HistoryRecordSnapshot:
    id: UUID
    record_type: HistoryRecordKind
    title: str
    created_at: datetime
    status: str
    version: int | None = None
    reason_code: str | None = None
    retry_at: datetime | None = None
    deadline: datetime | None = None
    inspection_id: UUID | None = None
    job_id: UUID | None = None
    download_id: UUID | None = None
    skill_id: str | None = None
    progress: int | None = None
    stage: str | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class HistoryRecordPage:
    items: tuple[HistoryRecordSnapshot, ...]
    next_cursor: HistoryRecordCursor | None


class HistoryRecordPersistence(Protocol):
    async def history(
        self,
        owner_hash: str,
        *,
        before: HistoryRecordCursor | None,
        limit: int,
    ) -> HistoryRecordPage: ...


class HistoryRecordService:
    def __init__(self, repository: HistoryRecordPersistence) -> None:
        self._repository = repository

    async def list(
        self,
        owner_hash: str,
        *,
        before: HistoryRecordCursor | None = None,
        limit: int = 20,
    ) -> HistoryRecordPage:
        validate_owner_hash(owner_hash)
        if not 1 <= limit <= 50:
            raise ValueError("invalid history page size")
        return await self._repository.history(owner_hash, before=before, limit=limit)
