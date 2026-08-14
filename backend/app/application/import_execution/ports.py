from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.domain.imports import ContentKind, ImportErrorCode

from .models import (
    ImportVerificationClaim,
    ImportWorkspace,
    VerifiedDocumentImport,
    VerifiedImportArtifact,
)


class ImportStoredObject(Protocol):
    @property
    def object_key(self) -> str: ...

    @property
    def last_modified(self) -> datetime: ...


class ImportExecutionRepository(Protocol):
    async def claim_verification(
        self,
        resource_id: UUID,
        content_kind: ContentKind,
        attempt: int,
        expected_version: int,
        *,
        worker_id: str,
        now: datetime,
        lease_for: timedelta,
    ) -> ImportVerificationClaim | None: ...

    async def heartbeat_verification(
        self,
        resource_id: UUID,
        attempt: int,
        *,
        worker_id: str,
        stage: str,
        progress: int,
        now: datetime,
        lease_for: timedelta,
    ) -> bool: ...

    async def complete_verification(
        self,
        claim: ImportVerificationClaim,
        artifact: VerifiedImportArtifact,
        *,
        worker_id: str,
        bucket: str,
        expires_at: datetime,
        now: datetime,
    ) -> None: ...

    async def fail_verification(
        self,
        claim: ImportVerificationClaim,
        error_code: ImportErrorCode,
        *,
        worker_id: str,
        now: datetime,
    ) -> None: ...

    async def recover_expired_verifications(
        self, now: datetime, *, limit: int
    ) -> tuple[UUID, ...]: ...

    async def expected_artifact_object_keys(self) -> frozenset[str]: ...


class ImportExecutionStorage(Protocol):
    async def download(self, object_key: str, target: Path) -> None: ...

    async def promote(
        self,
        source_key: str,
        destination_key: str,
        *,
        expected_size_bytes: int,
        sha256: str,
        content_type: str,
    ) -> object: ...

    async def upload_verified(
        self,
        source: Path,
        destination_key: str,
        *,
        expected_size_bytes: int,
        sha256: str,
        content_type: str,
    ) -> object: ...

    async def delete(self, object_key: str) -> None: ...

    async def list(self, prefix: str) -> tuple[ImportStoredObject, ...]: ...


class ImportWorkspaceManager(Protocol):
    async def create(self, task_id: str) -> ImportWorkspace: ...

    async def cleanup(self, task_id: str, workspace: Path | None) -> None: ...

    async def cleanup_orphans(
        self, now: datetime, *, older_than: timedelta, limit: int
    ) -> int: ...


class VideoImportVerifier(Protocol):
    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedImportArtifact: ...


class DocumentImportVerifier(Protocol):
    async def __call__(
        self, path: Path, claim: ImportVerificationClaim
    ) -> VerifiedDocumentImport: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...
