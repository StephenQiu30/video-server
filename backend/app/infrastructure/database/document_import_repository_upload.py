"""Multipart attempt allocation and activation for screenplay documents."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.imports import (
    BeginUploadAttemptResult,
    ImportAttemptSnapshot,
    ImportCleanupRef,
    ImportPersistenceConflict,
)
from app.domain.imports import ContentKind, ImportErrorCode, ImportStatus
from app.domain.imports.keys import quarantine_object_key

from .base import as_utc
from .document_import_mapping import attempt_snapshot
from .document_import_repository_support import (
    current_attempt,
    lock_attempt,
    lock_resource,
    require_document_kind,
    valid_upload_id,
    validate_part_plan,
)
from .models import DocumentImportAttemptRow


async def begin_upload_attempt(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
    *,
    part_size_bytes: int,
    part_count: int,
    expires_at: datetime,
    now: datetime,
) -> BeginUploadAttemptResult:
    require_document_kind(content_kind)
    validate_part_plan(part_size_bytes, part_count, expires_at, now)
    async with sessions() as session, session.begin():
        row = await lock_resource(session, resource_id, owner_hash)
        if row.status != ImportStatus.UPLOADING.value:
            raise ImportPersistenceConflict("document is not uploadable")
        superseded: tuple[ImportCleanupRef, ...] = ()
        current = await current_attempt(session, row, for_update=True)
        if current is not None and current.status == ImportStatus.UPLOADING.value:
            current.status = ImportStatus.EXPIRED.value
            current.error_code = ImportErrorCode.UPLOAD_SESSION_EXPIRED.value
            current.finished_at = now
            current.updated_at = now
            superseded = (ImportCleanupRef(current.object_key, current.upload_id),)
        next_attempt = row.attempt + 1
        attempt = DocumentImportAttemptRow(
            resource_id=row.id,
            attempt=next_attempt,
            status=ImportStatus.UPLOADING.value,
            object_key=quarantine_object_key(
                ContentKind.SCREENPLAY, row.id, next_attempt
            ),
            upload_id=None,
            content_type=row.content_type,
            declared_size_bytes=row.declared_size_bytes,
            part_size_bytes=part_size_bytes,
            part_count=part_count,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        session.add(attempt)
        row.attempt = next_attempt
        row.error_code = None
        row.version += 1
        row.updated_at = now
        await session.flush()
        return BeginUploadAttemptResult(attempt_snapshot(attempt), superseded)


async def activate_upload_attempt(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    owner_hash: str,
    content_kind: ContentKind,
    attempt: int,
    *,
    upload_id: str,
    now: datetime,
) -> ImportAttemptSnapshot:
    require_document_kind(content_kind)
    if not valid_upload_id(upload_id):
        raise ImportPersistenceConflict("invalid multipart upload id")
    async with sessions() as session, session.begin():
        row = await lock_resource(session, resource_id, owner_hash)
        current = await lock_attempt(session, row, attempt)
        if (
            row.status != ImportStatus.UPLOADING.value
            or current.status != ImportStatus.UPLOADING.value
            or row.attempt != attempt
            or as_utc(current.expires_at) <= as_utc(now)
        ):
            raise ImportPersistenceConflict("document upload attempt is not active")
        if current.upload_id is not None and current.upload_id != upload_id:
            raise ImportPersistenceConflict("document upload attempt is activated")
        current.upload_id = upload_id
        current.updated_at = now
        row.updated_at = now
        await session.flush()
        return attempt_snapshot(current)
