from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.services.storage_files.models import (
    StorageCleanupResult,
    StoredFileCategory,
    StoredFilePage,
)

DeleteStoredObject = Callable[[str], Awaitable[None]]


class StorageFileRepository(Protocol):
    async def list_files(self, *, page: int, page_size: int) -> StoredFilePage: ...

    async def delete_file(
        self,
        *,
        category: StoredFileCategory,
        file_id: UUID,
        now: datetime,
        delete: DeleteStoredObject,
    ) -> None: ...

    async def cleanup_before(
        self,
        cutoff: datetime,
        *,
        now: datetime,
        delete: DeleteStoredObject,
    ) -> StorageCleanupResult: ...
