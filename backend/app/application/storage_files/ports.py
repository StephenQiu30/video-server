from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol

from .models import StorageCleanupResult, StoredFilePage

DeleteStoredObject = Callable[[str], Awaitable[None]]


class StorageFileRepository(Protocol):
    async def list_files(self, *, page: int, page_size: int) -> StoredFilePage: ...

    async def cleanup_before(
        self,
        cutoff: datetime,
        *,
        now: datetime,
        delete: DeleteStoredObject,
    ) -> StorageCleanupResult: ...
