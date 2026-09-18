"""Cancellation transition for screenplay document imports."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.crud.document_import_mapping import cleanup_refs, resource_snapshot
from app.crud.document_import_repository_support import (
    current_attempt,
    lock_resource,
    require_document_kind,
)
from app.services.imports.errors import ImportPersistenceConflict
from app.services.imports.models import CancelImportResult
from app.services.imports.rules.enums import ContentKind, ImportStatus


async def cancel_resource(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
    *,
    now: datetime,
) -> CancelImportResult:
    require_document_kind(content_kind)
    async with sessions() as session, session.begin():
        row = await lock_resource(session, resource_id, owner_hash)
        current = await current_attempt(session, row, for_update=True)
        if row.status == ImportStatus.CANCELLED.value:
            return CancelImportResult(
                resource_snapshot(row, None), cleanup_refs(current)
            )
        if row.status not in {
            ImportStatus.UPLOADING.value,
            ImportStatus.VERIFYING.value,
        }:
            raise ImportPersistenceConflict("terminal document cannot be cancelled")
        if current is not None and current.status in {
            ImportStatus.UPLOADING.value,
            ImportStatus.VERIFYING.value,
        }:
            current.status = ImportStatus.CANCELLED.value
            current.error_code = None
            current.finished_at = now
            current.updated_at = now
        row.status = ImportStatus.CANCELLED.value
        row.error_code = None
        row.finished_at = now
        row.version += 1
        row.updated_at = now
        await session.flush()
        return CancelImportResult(resource_snapshot(row, None), cleanup_refs(current))
