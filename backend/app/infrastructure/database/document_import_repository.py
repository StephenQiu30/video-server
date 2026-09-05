"""Transactional upload-control persistence for screenplay documents."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.application.imports import (
    BeginUploadAttemptResult,
    CancelImportResult,
    ImportAttemptSnapshot,
    ImportResourceCreate,
    ImportResourceSaveResult,
    ImportResourceSnapshot,
)
from app.domain.imports import ContentKind, ImportErrorCode

from . import document_import_repository_cancel as cancellation
from . import document_import_repository_resources as resources
from . import document_import_repository_state as state
from . import document_import_repository_upload as upload
from .repository_base import RepositoryBase


class SqlAlchemyDocumentImportRepository(RepositoryBase):
    """Store owner-scoped document resources without a download projection."""

    async def create_resource(
        self, command: ImportResourceCreate, *, now: datetime
    ) -> ImportResourceSaveResult:
        return await resources.create_resource(
            self._sessions, command, now=now, quota_policy=self._quota_policy
        )

    async def get_resource(
        self, resource_id: UUID, owner_hash: str, content_kind: ContentKind
    ) -> ImportResourceSnapshot | None:
        return await resources.get_resource(
            self._sessions, resource_id, owner_hash, content_kind
        )

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
        return await upload.begin_upload_attempt(
            self._sessions,
            resource_id,
            owner_hash,
            content_kind,
            part_size_bytes=part_size_bytes,
            part_count=part_count,
            expires_at=expires_at,
            now=now,
        )

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
        return await upload.activate_upload_attempt(
            self._sessions,
            resource_id,
            owner_hash,
            content_kind,
            attempt,
            upload_id=upload_id,
            now=now,
        )

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
        return await state.mark_verifying(
            self._sessions,
            resource_id,
            owner_hash,
            content_kind,
            attempt,
            actual_size_bytes=actual_size_bytes,
            now=now,
        )

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
        return await state.fail_attempt(
            self._sessions,
            resource_id,
            owner_hash,
            content_kind,
            attempt,
            error_code=error_code,
            now=now,
        )

    async def expire_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        now: datetime,
    ) -> ImportResourceSnapshot:
        return await state.expire_attempt(
            self._sessions,
            resource_id,
            owner_hash,
            content_kind,
            attempt,
            now=now,
        )

    async def cancel_resource(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        *,
        now: datetime,
    ) -> CancelImportResult:
        return await cancellation.cancel_resource(
            self._sessions, resource_id, owner_hash, content_kind, now=now
        )
