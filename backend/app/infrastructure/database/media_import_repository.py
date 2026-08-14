"""Transactional persistence for browser MP4 import resources."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.imports import (
    BeginUploadAttemptResult,
    CancelImportResult,
    ImportAttemptSnapshot,
    ImportCleanupRef,
    ImportPersistenceConflict,
    ImportPersistenceIdempotencyConflict,
    ImportPersistenceNotFound,
    ImportResourceCreate,
    ImportResourceSaveResult,
    ImportResourceSnapshot,
)
from app.application.imports.events import (
    CONTENT_IMPORT_VERIFY_REQUESTED,
    import_verify_requested_payload,
)
from app.domain.imports import (
    ContentKind,
    ImportErrorCode,
    ImportSourceFormat,
    ImportStatus,
    quarantine_object_key,
)

from .base import as_utc
from .models import (
    DownloadJobRow,
    MediaImportAttemptRow,
    MediaImportRow,
    OutboxEventRow,
)
from .repository_base import RepositoryBase


class SqlAlchemyMediaImportRepository(RepositoryBase):
    """Store the video-import aggregate and its download projection atomically."""

    async def create_resource(
        self, command: ImportResourceCreate, *, now: datetime
    ) -> ImportResourceSaveResult:
        _require_video_create(command)
        async with self._sessions() as session:
            try:
                async with session.begin():
                    existing = await session.scalar(self._idempotency_query(command))
                    if existing is not None:
                        return await self._idempotent_result(session, existing, command)
                    job = DownloadJobRow(
                        id=command.id,
                        source_kind="browser_import",
                        inspection_id=None,
                        format_id=None,
                        owner_hash=command.owner_hash,
                        idempotency_key=f"browser-import:{command.id}",
                        request_fingerprint=command.request_fingerprint,
                        semantic_plan={
                            "source_kind": "browser_import",
                            "container": "mp4",
                        },
                        status="running",
                        stage="downloading",
                        stage_rank=2,
                        progress=0,
                        attempt=0,
                        max_attempts=1,
                        version=0,
                        started_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    row = MediaImportRow(
                        id=command.id,
                        owner_hash=command.owner_hash,
                        idempotency_key=command.idempotency_key,
                        request_fingerprint=command.request_fingerprint,
                        source_format=command.source_format.value,
                        display_name=command.display_name,
                        content_type=command.content_type,
                        declared_size_bytes=command.declared_size_bytes,
                        declared_sha256=command.declared_sha256,
                        rights_statement_version=command.rights_statement_version,
                        status=ImportStatus.UPLOADING.value,
                        attempt=0,
                        version=0,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add_all((job, row))
                    await session.flush()
                    result = ImportResourceSaveResult(
                        _resource_snapshot(row, None), created=True
                    )
                return result
            except IntegrityError as exc:
                await session.rollback()
                existing = await session.scalar(self._idempotency_query(command))
                if existing is None:
                    raise
                try:
                    return await self._idempotent_result(session, existing, command)
                except ImportPersistenceIdempotencyConflict as conflict:
                    raise conflict from exc

    async def get_resource(
        self, resource_id: UUID, owner_hash: str, content_kind: ContentKind
    ) -> ImportResourceSnapshot | None:
        if content_kind is not ContentKind.VIDEO:
            return None
        async with self._sessions() as session:
            row = await session.scalar(
                select(MediaImportRow).where(
                    MediaImportRow.id == resource_id,
                    MediaImportRow.owner_hash == owner_hash,
                )
            )
            if row is None:
                return None
            attempt = await _current_attempt(session, row)
            return _resource_snapshot(row, _visible_attempt(attempt))

    async def begin_upload_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        *,
        part_size_bytes: int,
        part_count: int,
        expires_at: datetime,
        now: datetime,
    ) -> BeginUploadAttemptResult:
        _require_video_kind(content_kind)
        _validate_part_plan(part_size_bytes, part_count, expires_at, now)
        async with self._sessions() as session, session.begin():
            row = await _lock_resource(session, resource_id, owner_hash)
            if row.status != ImportStatus.UPLOADING.value:
                raise ImportPersistenceConflict("media import is not uploadable")
            superseded: tuple[ImportCleanupRef, ...] = ()
            current = await _current_attempt(session, row, for_update=True)
            if current is not None and current.status == ImportStatus.UPLOADING.value:
                current.status = ImportStatus.EXPIRED.value
                current.error_code = ImportErrorCode.UPLOAD_SESSION_EXPIRED.value
                current.finished_at = now
                current.updated_at = now
                superseded = (ImportCleanupRef(current.object_key, current.upload_id),)
            next_attempt = row.attempt + 1
            attempt = MediaImportAttemptRow(
                resource_id=row.id,
                attempt=next_attempt,
                status=ImportStatus.UPLOADING.value,
                object_key=quarantine_object_key(
                    ContentKind.VIDEO, row.id, next_attempt
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
            job = await _lock_job(session, row.id)
            _set_job_uploading(job, now)
            await session.flush()
            return BeginUploadAttemptResult(_attempt_snapshot(attempt), superseded)

    async def activate_upload_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        upload_id: str,
        now: datetime,
    ) -> ImportAttemptSnapshot:
        _require_video_kind(content_kind)
        if not _valid_upload_id(upload_id):
            raise ImportPersistenceConflict("invalid multipart upload id")
        async with self._sessions() as session, session.begin():
            row = await _lock_resource(session, resource_id, owner_hash)
            current = await _lock_attempt(session, row, attempt)
            if (
                row.status != ImportStatus.UPLOADING.value
                or current.status != ImportStatus.UPLOADING.value
                or row.attempt != attempt
                or as_utc(current.expires_at) <= as_utc(now)
            ):
                raise ImportPersistenceConflict("upload attempt is no longer active")
            if current.upload_id is not None and current.upload_id != upload_id:
                raise ImportPersistenceConflict("upload attempt is already activated")
            current.upload_id = upload_id
            current.updated_at = now
            row.updated_at = now
            await session.flush()
            return _attempt_snapshot(current)

    async def mark_verifying(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        actual_size_bytes: int,
        now: datetime,
    ) -> ImportResourceSnapshot:
        _require_video_kind(content_kind)
        async with self._sessions() as session, session.begin():
            row = await _lock_resource(session, resource_id, owner_hash)
            current = await _lock_attempt(session, row, attempt)
            if row.status == ImportStatus.VERIFYING.value:
                if (
                    row.attempt != attempt
                    or current.status != ImportStatus.VERIFYING.value
                    or current.actual_size_bytes != actual_size_bytes
                ):
                    raise ImportPersistenceConflict(
                        "completed upload differs from stored verification"
                    )
                return _resource_snapshot(row, current)
            if (
                row.status != ImportStatus.UPLOADING.value
                or row.attempt != attempt
                or current.status != ImportStatus.UPLOADING.value
                or current.upload_id is None
                or actual_size_bytes != row.declared_size_bytes
            ):
                raise ImportPersistenceConflict("upload attempt cannot be verified")
            current.status = ImportStatus.VERIFYING.value
            current.actual_size_bytes = actual_size_bytes
            current.completed_at = now
            current.error_code = None
            current.updated_at = now
            row.status = ImportStatus.VERIFYING.value
            row.error_code = None
            row.version += 1
            row.updated_at = now
            job = await _lock_job(session, row.id)
            job.status = "running"
            job.stage = "verifying"
            job.stage_rank = 4
            job.progress = max(job.progress, 50)
            job.version += 1
            job.error_code = None
            job.error_message = None
            job.updated_at = now
            session.add(
                OutboxEventRow(
                    id=uuid4(),
                    aggregate_type="media_import",
                    aggregate_id=row.id,
                    event_type=CONTENT_IMPORT_VERIFY_REQUESTED,
                    payload=import_verify_requested_payload(
                        row.id, ContentKind.VIDEO, attempt, row.version
                    ),
                    available_at=now,
                    created_at=now,
                )
            )
            await session.flush()
            return _resource_snapshot(row, current)

    async def fail_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        error_code: ImportErrorCode,
        now: datetime,
    ) -> ImportResourceSnapshot:
        _require_video_kind(content_kind)
        async with self._sessions() as session, session.begin():
            row = await _lock_resource(session, resource_id, owner_hash)
            current = await _lock_attempt(session, row, attempt)
            if (
                current.status == ImportStatus.FAILED.value
                and current.error_code == error_code.value
                and row.error_code == error_code.value
            ):
                return _resource_snapshot(row, None)
            if (
                row.attempt != attempt
                or row.status != ImportStatus.UPLOADING.value
                or current.status != ImportStatus.UPLOADING.value
            ):
                raise ImportPersistenceConflict("upload attempt cannot be failed")
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
            job = await _lock_job(session, row.id)
            if error_code.retryable:
                _set_job_uploading(job, now, error_code="storage_unavailable")
            else:
                _set_job_failed(job, now, error_code="media_validation_failed")
            await session.flush()
            return _resource_snapshot(row, None)

    async def expire_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        now: datetime,
    ) -> ImportResourceSnapshot:
        _require_video_kind(content_kind)
        async with self._sessions() as session, session.begin():
            row = await _lock_resource(session, resource_id, owner_hash)
            current = await _lock_attempt(session, row, attempt)
            if (
                current.status == ImportStatus.EXPIRED.value
                and row.status == ImportStatus.UPLOADING.value
            ):
                return _resource_snapshot(row, None)
            if (
                row.status != ImportStatus.UPLOADING.value
                or row.attempt != attempt
                or current.status != ImportStatus.UPLOADING.value
                or as_utc(current.expires_at) > as_utc(now)
            ):
                raise ImportPersistenceConflict("upload attempt cannot be expired")
            current.status = ImportStatus.EXPIRED.value
            current.error_code = ImportErrorCode.UPLOAD_SESSION_EXPIRED.value
            current.finished_at = now
            current.updated_at = now
            row.error_code = ImportErrorCode.UPLOAD_SESSION_EXPIRED.value
            row.version += 1
            row.updated_at = now
            job = await _lock_job(session, row.id)
            _set_job_uploading(job, now)
            await session.flush()
            return _resource_snapshot(row, None)

    async def cancel_resource(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        *,
        now: datetime,
    ) -> CancelImportResult:
        _require_video_kind(content_kind)
        async with self._sessions() as session, session.begin():
            row = await _lock_resource(session, resource_id, owner_hash)
            current = await _current_attempt(session, row, for_update=True)
            if row.status == ImportStatus.CANCELLED.value:
                return CancelImportResult(
                    _resource_snapshot(row, None), _cleanup_refs(current)
                )
            if row.status not in {
                ImportStatus.UPLOADING.value,
                ImportStatus.VERIFYING.value,
            }:
                raise ImportPersistenceConflict("terminal media import cannot cancel")
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
            job = await _lock_job(session, row.id)
            job.status = "cancelled"
            job.stage = None
            job.stage_rank = 0
            job.version += 1
            job.cancel_requested_at = now
            job.finished_at = now
            job.error_code = "cancelled"
            job.error_message = None
            job.lease_owner = None
            job.lease_expires_at = None
            job.updated_at = now
            await session.flush()
            return CancelImportResult(
                _resource_snapshot(row, None), _cleanup_refs(current)
            )

    @staticmethod
    def _idempotency_query(
        command: ImportResourceCreate,
    ) -> Select[tuple[MediaImportRow]]:
        return select(MediaImportRow).where(
            MediaImportRow.owner_hash == command.owner_hash,
            MediaImportRow.idempotency_key == command.idempotency_key,
        )

    @staticmethod
    async def _idempotent_result(
        session: AsyncSession,
        row: MediaImportRow,
        command: ImportResourceCreate,
    ) -> ImportResourceSaveResult:
        if row.request_fingerprint != command.request_fingerprint:
            raise ImportPersistenceIdempotencyConflict(
                "media import idempotency key already used"
            )
        attempt = await _current_attempt(session, row)
        return ImportResourceSaveResult(
            _resource_snapshot(row, _visible_attempt(attempt)), created=False
        )


def _require_video_create(command: ImportResourceCreate) -> None:
    if (
        command.content_kind is not ContentKind.VIDEO
        or command.source_format is not ImportSourceFormat.MP4
        or command.content_type != ImportSourceFormat.MP4.content_type
    ):
        raise ImportPersistenceConflict(
            "media import repository only accepts browser MP4 resources"
        )


def _require_video_kind(content_kind: ContentKind) -> None:
    if content_kind is not ContentKind.VIDEO:
        raise ImportPersistenceNotFound("media import does not exist")


def _validate_part_plan(
    part_size_bytes: int, part_count: int, expires_at: datetime, now: datetime
) -> None:
    if (
        isinstance(part_size_bytes, bool)
        or not 5 * 1024**2 <= part_size_bytes <= 5 * 1024**3
        or isinstance(part_count, bool)
        or not 1 <= part_count <= 10_000
        or as_utc(expires_at) <= as_utc(now)
    ):
        raise ImportPersistenceConflict("invalid upload part plan")


def _valid_upload_id(upload_id: str) -> bool:
    return (
        bool(upload_id)
        and len(upload_id) <= 1024
        and all(ord(character) >= 0x20 for character in upload_id)
    )


async def _lock_resource(
    session: AsyncSession, resource_id: UUID, owner_hash: str
) -> MediaImportRow:
    row = await session.scalar(
        select(MediaImportRow)
        .where(
            MediaImportRow.id == resource_id,
            MediaImportRow.owner_hash == owner_hash,
        )
        .with_for_update()
    )
    if row is None:
        raise ImportPersistenceNotFound("media import does not exist")
    return row


async def _lock_job(session: AsyncSession, resource_id: UUID) -> DownloadJobRow:
    row = await session.scalar(
        select(DownloadJobRow)
        .where(
            DownloadJobRow.id == resource_id,
            DownloadJobRow.source_kind == "browser_import",
        )
        .with_for_update()
    )
    if row is None:
        raise ImportPersistenceConflict("browser import download job is missing")
    return row


async def _lock_attempt(
    session: AsyncSession, resource: MediaImportRow, attempt: int
) -> MediaImportAttemptRow:
    row = await session.scalar(
        select(MediaImportAttemptRow)
        .where(
            MediaImportAttemptRow.resource_id == resource.id,
            MediaImportAttemptRow.attempt == attempt,
        )
        .with_for_update()
    )
    if row is None:
        raise ImportPersistenceConflict("media import attempt does not exist")
    return row


async def _current_attempt(
    session: AsyncSession, resource: MediaImportRow, *, for_update: bool = False
) -> MediaImportAttemptRow | None:
    if resource.attempt <= 0:
        return None
    statement: Select[tuple[MediaImportAttemptRow]] = select(
        MediaImportAttemptRow
    ).where(
        MediaImportAttemptRow.resource_id == resource.id,
        MediaImportAttemptRow.attempt == resource.attempt,
    )
    if for_update:
        statement = statement.with_for_update()
    return cast(MediaImportAttemptRow | None, await session.scalar(statement))


def _visible_attempt(
    row: MediaImportAttemptRow | None,
) -> MediaImportAttemptRow | None:
    if row is None or row.status not in {
        ImportStatus.UPLOADING.value,
        ImportStatus.VERIFYING.value,
    }:
        return None
    return row


def _resource_snapshot(
    row: MediaImportRow, attempt: MediaImportAttemptRow | None
) -> ImportResourceSnapshot:
    return ImportResourceSnapshot(
        id=row.id,
        owner_hash=row.owner_hash,
        content_kind=ContentKind.VIDEO.value,
        source_format=row.source_format,
        display_name=row.display_name,
        declared_size_bytes=row.declared_size_bytes,
        declared_sha256=row.declared_sha256,
        status=row.status,
        attempt=row.attempt,
        error_code=row.error_code,
        version=row.version,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
        finished_at=(None if row.finished_at is None else as_utc(row.finished_at)),
        active_attempt=None if attempt is None else _attempt_snapshot(attempt),
    )


def _attempt_snapshot(row: MediaImportAttemptRow) -> ImportAttemptSnapshot:
    return ImportAttemptSnapshot(
        resource_id=row.resource_id,
        content_kind=ContentKind.VIDEO.value,
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


def _cleanup_refs(
    row: MediaImportAttemptRow | None,
) -> tuple[ImportCleanupRef, ...]:
    if row is None:
        return ()
    return (ImportCleanupRef(row.object_key, row.upload_id),)


def _set_job_uploading(
    row: DownloadJobRow, now: datetime, *, error_code: str | None = None
) -> None:
    row.status = "running"
    row.stage = "downloading"
    row.stage_rank = 2
    row.progress = 0
    row.version += 1
    row.finished_at = None
    row.error_code = error_code
    row.error_message = None
    row.updated_at = now


def _set_job_failed(row: DownloadJobRow, now: datetime, *, error_code: str) -> None:
    row.status = "failed"
    row.stage = None
    row.stage_rank = 0
    row.version += 1
    row.finished_at = now
    row.error_code = error_code
    row.error_message = None
    row.updated_at = now
