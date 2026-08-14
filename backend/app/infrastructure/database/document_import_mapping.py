"""Snapshot mapping for screenplay document imports."""

from __future__ import annotations

from pathlib import PurePath

from app.application.imports import (
    ImportAttemptSnapshot,
    ImportCleanupRef,
    ImportResourceSnapshot,
)
from app.domain.imports import ContentKind, ImportStatus

from .base import as_utc
from .models import DocumentImportAttemptRow, DocumentRow


def document_title(filename: str) -> str:
    stem = PurePath(filename).stem.strip()
    return stem or filename


def resource_snapshot(
    row: DocumentRow, attempt: DocumentImportAttemptRow | None
) -> ImportResourceSnapshot:
    return ImportResourceSnapshot(
        id=row.id,
        owner_hash=row.owner_hash,
        content_kind=ContentKind.SCREENPLAY.value,
        source_format=row.source_format,
        display_name=row.original_filename,
        declared_size_bytes=row.declared_size_bytes,
        declared_sha256=row.declared_sha256,
        status=row.status,
        attempt=row.attempt,
        error_code=row.error_code,
        version=row.version,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
        finished_at=None if row.finished_at is None else as_utc(row.finished_at),
        active_attempt=None if attempt is None else attempt_snapshot(attempt),
    )


def attempt_snapshot(row: DocumentImportAttemptRow) -> ImportAttemptSnapshot:
    return ImportAttemptSnapshot(
        resource_id=row.resource_id,
        content_kind=ContentKind.SCREENPLAY.value,
        attempt=row.attempt,
        status=row.status,
        object_key=row.object_key,
        upload_id=row.upload_id,
        content_type=row.content_type,
        declared_size_bytes=row.declared_size_bytes,
        part_size_bytes=row.part_size_bytes,
        part_count=row.part_count,
        expires_at=as_utc(row.expires_at),
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )


def visible_attempt(
    row: DocumentImportAttemptRow | None,
) -> DocumentImportAttemptRow | None:
    if row is None or row.status not in {
        ImportStatus.UPLOADING.value,
        ImportStatus.VERIFYING.value,
    }:
        return None
    return row


def cleanup_refs(
    row: DocumentImportAttemptRow | None,
) -> tuple[ImportCleanupRef, ...]:
    if row is None:
        return ()
    return (ImportCleanupRef(row.object_key, row.upload_id),)
