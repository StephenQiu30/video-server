"""Verification handoff and terminal upload state for screenplay documents."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.imports import ImportPersistenceConflict, ImportResourceSnapshot
from app.application.imports.events import (
    CONTENT_IMPORT_VERIFY_REQUESTED,
    import_verify_requested_payload,
)
from app.domain.imports import ContentKind, ImportErrorCode, ImportStatus

from .base import as_utc
from .document_import_mapping import resource_snapshot
from .document_import_repository_support import (
    lock_attempt,
    lock_resource,
    require_document_kind,
)
from .models import OutboxEventRow


async def mark_verifying(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
    attempt: int,
    *,
    actual_size_bytes: int,
    now: datetime,
) -> ImportResourceSnapshot:
    require_document_kind(content_kind)
    async with sessions() as session, session.begin():
        row = await lock_resource(session, resource_id, owner_hash)
        current = await lock_attempt(session, row, attempt)
        if row.status == ImportStatus.VERIFYING.value:
            if (
                row.attempt != attempt
                or current.status != ImportStatus.VERIFYING.value
                or current.actual_size_bytes != actual_size_bytes
            ):
                raise ImportPersistenceConflict(
                    "completed document differs from stored verification"
                )
            return resource_snapshot(row, current)
        if (
            row.status != ImportStatus.UPLOADING.value
            or row.attempt != attempt
            or current.status != ImportStatus.UPLOADING.value
            or current.upload_id is None
            or actual_size_bytes != row.declared_size_bytes
        ):
            raise ImportPersistenceConflict("document upload cannot be verified")
        current.status = ImportStatus.VERIFYING.value
        current.actual_size_bytes = actual_size_bytes
        current.completed_at = now
        current.error_code = None
        current.updated_at = now
        row.status = ImportStatus.VERIFYING.value
        row.error_code = None
        row.version += 1
        row.updated_at = now
        session.add(
            OutboxEventRow(
                id=uuid4(),
                aggregate_type="document",
                aggregate_id=row.id,
                event_type=CONTENT_IMPORT_VERIFY_REQUESTED,
                payload=import_verify_requested_payload(
                    row.id, ContentKind.SCREENPLAY, attempt, row.version
                ),
                available_at=now,
                created_at=now,
            )
        )
        await session.flush()
        return resource_snapshot(row, current)


async def fail_attempt(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
    attempt: int,
    *,
    error_code: ImportErrorCode,
    now: datetime,
) -> ImportResourceSnapshot:
    require_document_kind(content_kind)
    async with sessions() as session, session.begin():
        row = await lock_resource(session, resource_id, owner_hash)
        current = await lock_attempt(session, row, attempt)
        if (
            current.status == ImportStatus.FAILED.value
            and current.error_code == error_code.value
            and row.error_code == error_code.value
        ):
            return resource_snapshot(row, None)
        if (
            row.attempt != attempt
            or row.status != ImportStatus.UPLOADING.value
            or current.status != ImportStatus.UPLOADING.value
        ):
            raise ImportPersistenceConflict("document upload cannot be failed")
        current.status = ImportStatus.FAILED.value
        current.error_code = error_code.value
        current.finished_at = now
        current.updated_at = now
        row.status = (
            ImportStatus.UPLOADING.value
            if error_code.retryable
            else ImportStatus.FAILED.value
        )
        row.error_code = error_code.value
        row.finished_at = None if error_code.retryable else now
        row.version += 1
        row.updated_at = now
        await session.flush()
        return resource_snapshot(row, None)


async def expire_attempt(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
    attempt: int,
    *,
    now: datetime,
) -> ImportResourceSnapshot:
    require_document_kind(content_kind)
    async with sessions() as session, session.begin():
        row = await lock_resource(session, resource_id, owner_hash)
        current = await lock_attempt(session, row, attempt)
        if (
            current.status == ImportStatus.EXPIRED.value
            and row.status == ImportStatus.UPLOADING.value
        ):
            return resource_snapshot(row, None)
        if (
            row.status != ImportStatus.UPLOADING.value
            or row.attempt != attempt
            or current.status != ImportStatus.UPLOADING.value
            or as_utc(current.expires_at) > as_utc(now)
        ):
            raise ImportPersistenceConflict("document upload cannot be expired")
        current.status = ImportStatus.EXPIRED.value
        current.error_code = ImportErrorCode.UPLOAD_SESSION_EXPIRED.value
        current.finished_at = now
        current.updated_at = now
        row.error_code = ImportErrorCode.UPLOAD_SESSION_EXPIRED.value
        row.version += 1
        row.updated_at = now
        await session.flush()
        return resource_snapshot(row, None)
