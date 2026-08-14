"""Read port for owner-scoped screenplay documents."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from .models import DocumentDeletionPlan, DocumentPageSnapshot, DocumentSnapshot


class DocumentPreviewStorage(Protocol):
    @property
    def bucket(self) -> str: ...

    async def read_range(self, object_key: str, *, length: int) -> bytes: ...


class DocumentReader(Protocol):
    async def get_document(
        self, document_id: UUID, owner_hash: str
    ) -> DocumentSnapshot | None: ...

    async def list_documents(
        self, owner_hash: str, *, page: int, page_size: int
    ) -> DocumentPageSnapshot: ...


class DocumentDeletionRepository(Protocol):
    async def prepare_document_deletion(
        self, document_id: UUID, owner_hash: str, *, now: datetime
    ) -> DocumentDeletionPlan: ...

    async def finish_document_deletion(
        self,
        document_id: UUID,
        owner_hash: str,
        *,
        object_keys: tuple[str, ...],
        now: datetime,
    ) -> None: ...
