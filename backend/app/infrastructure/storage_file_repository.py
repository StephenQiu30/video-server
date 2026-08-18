from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.storage_files import StorageCleanupResult, StoredFilePage
from app.application.storage_files.ports import DeleteStoredObject
from app.infrastructure.storage_file_cleanup_reports import cleanup_reports
from app.infrastructure.storage_file_cleanup_sources import (
    cleanup_documents,
    cleanup_videos,
)
from app.infrastructure.storage_file_queries import list_stored_files


class SqlAlchemyStorageFileRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_files(self, *, page: int, page_size: int) -> StoredFilePage:
        return await list_stored_files(self._sessions, page=page, page_size=page_size)

    async def cleanup_before(
        self,
        cutoff: datetime,
        *,
        now: datetime,
        delete: DeleteStoredObject,
    ) -> StorageCleanupResult:
        totals = [0, 0, 0, 0]
        for cleaner in (cleanup_videos, cleanup_documents, cleanup_reports):
            result = await cleaner(self._sessions, cutoff, now, delete)
            totals = [left + right for left, right in zip(totals, result, strict=True)]
        return StorageCleanupResult(
            older_than_days=0,
            removed_resources=totals[0],
            removed_objects=totals[1],
            freed_bytes=totals[2],
            failed_resources=totals[3],
        )
