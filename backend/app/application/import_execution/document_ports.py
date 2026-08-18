from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.domain.imports import ContentKind, ImportErrorCode

from .models import ImportVerificationClaim, VerifiedDocumentImport


class DocumentImportExecutionRepository(Protocol):
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
        artifact: VerifiedDocumentImport,
        *,
        worker_id: str,
        bucket: str,
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
