from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.imports import ContentKind, ImportErrorCode

from .models import (
    BeginUploadAttemptResult,
    CancelImportResult,
    CompletedUploadPart,
    ImportAttemptSnapshot,
    ImportResourceCreate,
    ImportResourceSaveResult,
    ImportResourceSnapshot,
)


class ObjectHead(Protocol):
    @property
    def size_bytes(self) -> int: ...

    @property
    def sha256(self) -> str | None: ...

    @property
    def content_type(self) -> str | None: ...


class ImportRepository(Protocol):
    async def create_resource(
        self, command: ImportResourceCreate, *, now: datetime
    ) -> ImportResourceSaveResult: ...

    async def get_resource(
        self, resource_id: UUID, owner_hash: str, content_kind: ContentKind
    ) -> ImportResourceSnapshot | None: ...

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
    ) -> BeginUploadAttemptResult: ...

    async def activate_upload_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        upload_id: str,
        now: datetime,
    ) -> ImportAttemptSnapshot: ...

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
        """Atomically update state and enqueue content.import.verify.requested."""
        ...

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
        """Fail one attempt; retryable errors may leave the resource uploadable."""
        ...

    async def expire_attempt(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        attempt: int,
        *,
        now: datetime,
    ) -> ImportResourceSnapshot:
        """Expire one upload session while leaving the resource refreshable."""
        ...

    async def cancel_resource(
        self,
        resource_id: UUID,
        owner_hash: str,
        content_kind: ContentKind,
        *,
        now: datetime,
    ) -> CancelImportResult: ...


class QuarantineObjectStorage(Protocol):
    async def create_multipart_upload(
        self,
        object_key: str,
        *,
        content_type: str,
        declared_sha256: str | None = None,
    ) -> str: ...

    async def presign_upload_part(
        self,
        object_key: str,
        upload_id: str,
        part_number: int,
        *,
        ttl_seconds: int,
        size_bytes: int,
        use_local_browser_endpoint: bool = False,
    ) -> str: ...

    async def complete_multipart_upload(
        self,
        object_key: str,
        upload_id: str,
        parts: tuple[CompletedUploadPart, ...],
    ) -> str | None: ...

    async def abort_multipart_upload(self, object_key: str, upload_id: str) -> None: ...

    async def stat(self, object_key: str) -> ObjectHead | None: ...

    async def delete(self, object_key: str) -> None: ...


class RequestFingerprinter(Protocol):
    def fingerprint(self, namespace: str, *values: str) -> str: ...


type Clock = Callable[[], datetime]
type IdFactory = Callable[[], UUID]
