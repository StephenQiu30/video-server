from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from app.services.storage_files.models import (
    StorageCleanupResult,
    StoredFileCategory,
    StoredFilePage,
)
from app.services.storage_files.ports import DeleteStoredObject, StorageFileRepository


class StorageFileService:
    def __init__(
        self,
        repository: StorageFileRepository,
        delete: DeleteStoredObject,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._delete = delete
        self._now = now

    async def list_files(self, *, page: int = 1, page_size: int = 20) -> StoredFilePage:
        if not 1 <= page <= 10_000 or not 1 <= page_size <= 50:
            raise ValueError("invalid pagination")
        return await self._repository.list_files(page=page, page_size=page_size)

    async def delete_file(
        self, *, category: StoredFileCategory, file_id: UUID
    ) -> None:
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("deletion clock must be timezone-aware")
        await self._repository.delete_file(
            category=category,
            file_id=file_id,
            now=now,
            delete=self._delete,
        )

    async def cleanup(self, *, older_than_days: int = 30) -> StorageCleanupResult:
        if not 1 <= older_than_days <= 3_650:
            raise ValueError("invalid cleanup age")
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("cleanup clock must be timezone-aware")
        result = await self._repository.cleanup_before(
            now - timedelta(days=older_than_days),
            now=now,
            delete=self._delete,
        )
        return StorageCleanupResult(
            older_than_days=older_than_days,
            removed_resources=result.removed_resources,
            removed_objects=result.removed_objects,
            freed_bytes=result.freed_bytes,
            failed_resources=result.failed_resources,
        )
