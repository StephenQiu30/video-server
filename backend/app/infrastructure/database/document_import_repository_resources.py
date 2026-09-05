"""Creation and owned reads for screenplay document imports."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.imports import (
    ImportPersistenceIdempotencyConflict,
    ImportResourceCreate,
    ImportResourceSaveResult,
    ImportResourceSnapshot,
)
from app.application.quotas import QuotaPolicy
from app.domain.imports import ContentKind, ImportStatus

from .document_import_mapping import (
    document_title,
    resource_snapshot,
    visible_attempt,
)
from .document_import_repository_support import (
    current_attempt,
    require_document_create,
)
from .models import DocumentRow
from .quota_admission import lock_admission, reserve


async def create_resource(
    sessions: async_sessionmaker[AsyncSession],
    command: ImportResourceCreate,
    *,
    now: datetime,
    quota_policy: QuotaPolicy,
) -> ImportResourceSaveResult:
    require_document_create(command)
    async with sessions() as session:
        try:
            async with session.begin():
                await lock_admission(session, command.owner_hash)
                existing = await session.scalar(idempotency_query(command))
                if existing is not None:
                    return await idempotent_result(session, existing, command)
                await reserve(
                    session,
                    quota_policy,
                    owner_hash=command.owner_hash,
                    resource_id=command.id,
                    kind="document_import",
                    size_bytes=command.declared_size_bytes,
                    now=now,
                )
                row = DocumentRow(
                    id=command.id,
                    owner_hash=command.owner_hash,
                    idempotency_key=command.idempotency_key,
                    request_fingerprint=command.request_fingerprint,
                    title=document_title(command.display_name),
                    original_filename=command.display_name,
                    source_format=command.source_format.value,
                    content_type=command.content_type,
                    declared_size_bytes=command.declared_size_bytes,
                    declared_sha256=command.declared_sha256,
                    rights_statement_version=command.rights_statement_version,
                    status=ImportStatus.UPLOADING.value,
                    attempt=0,
                    version=0,
                    quality_warnings=[],
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                await session.flush()
                result = ImportResourceSaveResult(
                    resource_snapshot(row, None), created=True
                )
            return result
        except IntegrityError as exc:
            await session.rollback()
            existing = await session.scalar(idempotency_query(command))
            if existing is None:
                raise
            try:
                return await idempotent_result(session, existing, command)
            except ImportPersistenceIdempotencyConflict as conflict:
                raise conflict from exc


async def get_resource(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
) -> ImportResourceSnapshot | None:
    if content_kind is not ContentKind.SCREENPLAY:
        return None
    async with sessions() as session:
        row = await session.scalar(
            select(DocumentRow).where(
                DocumentRow.id == resource_id,
                DocumentRow.owner_hash == owner_hash,
                DocumentRow.deleted_at.is_(None),
            )
        )
        if row is None:
            return None
        attempt = await current_attempt(session, row)
        return resource_snapshot(row, visible_attempt(attempt))


def idempotency_query(command: ImportResourceCreate) -> Select[tuple[DocumentRow]]:
    return select(DocumentRow).where(
        DocumentRow.owner_hash == command.owner_hash,
        DocumentRow.idempotency_key == command.idempotency_key,
    )


async def idempotent_result(
    session: AsyncSession, row: DocumentRow, command: ImportResourceCreate
) -> ImportResourceSaveResult:
    if row.request_fingerprint != command.request_fingerprint:
        raise ImportPersistenceIdempotencyConflict(
            "document idempotency key already used"
        )
    attempt = await current_attempt(session, row)
    return ImportResourceSaveResult(
        resource_snapshot(row, visible_attempt(attempt)), created=False
    )
