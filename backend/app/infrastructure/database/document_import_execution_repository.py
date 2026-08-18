from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from app.application.import_execution import (
    ImportVerificationClaim,
    VerifiedDocumentImport,
)
from app.domain.imports import ContentKind, ImportErrorCode

from . import document_execution_lease as lease
from . import document_execution_state as state
from .repository_base import RepositoryBase


class SqlAlchemyDocumentImportExecutionRepository(RepositoryBase):
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
    ) -> ImportVerificationClaim | None:
        return await lease.claim_verification(
            self._sessions,
            resource_id,
            content_kind,
            attempt,
            expected_version,
            worker_id=worker_id,
            now=now,
            lease_for=lease_for,
        )

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
    ) -> bool:
        return await lease.heartbeat_verification(
            self._sessions,
            resource_id,
            attempt,
            worker_id=worker_id,
            stage=stage,
            progress=progress,
            now=now,
            lease_for=lease_for,
        )

    async def complete_verification(
        self,
        claim: ImportVerificationClaim,
        artifact: VerifiedDocumentImport,
        *,
        worker_id: str,
        bucket: str,
        now: datetime,
    ) -> None:
        await state.complete_verification(
            self._sessions,
            claim,
            artifact,
            worker_id=worker_id,
            bucket=bucket,
            now=now,
        )

    async def fail_verification(
        self,
        claim: ImportVerificationClaim,
        error_code: ImportErrorCode,
        *,
        worker_id: str,
        now: datetime,
    ) -> None:
        await state.fail_verification(
            self._sessions,
            claim,
            error_code,
            worker_id=worker_id,
            now=now,
        )

    async def recover_expired_verifications(
        self, now: datetime, *, limit: int
    ) -> tuple[UUID, ...]:
        return await lease.recover_expired_verifications(
            self._sessions, now, limit=limit
        )

    async def expected_artifact_object_keys(self) -> frozenset[str]:
        return await state.expected_artifact_object_keys(self._sessions)
