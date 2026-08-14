from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.import_execution import ImportVerificationClaim
from app.application.imports.events import (
    CONTENT_IMPORT_VERIFY_REQUESTED,
    import_verify_requested_payload,
)
from app.domain.imports import ContentKind, ImportStatus

from .base import as_utc
from .document_execution_support import (
    clear_lease,
    lock_attempt,
    lock_document,
    owns,
    validate_claim_arguments,
    validate_heartbeat,
    verification_claim,
)
from .models import DocumentImportAttemptRow, DocumentRow, OutboxEventRow


async def claim_verification(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    content_kind: ContentKind,
    attempt: int,
    expected_version: int,
    *,
    worker_id: str,
    now: datetime,
    lease_for: timedelta,
) -> ImportVerificationClaim | None:
    validate_claim_arguments(
        content_kind, attempt, expected_version, worker_id, lease_for
    )
    async with sessions() as session, session.begin():
        row = await session.scalar(
            select(DocumentRow).where(DocumentRow.id == resource_id).with_for_update()
        )
        if row is None or (
            row.status != ImportStatus.VERIFYING.value
            or row.attempt != attempt
            or row.version != expected_version
        ):
            return None
        current = await lock_attempt(session, row.id, attempt)
        if current.status != ImportStatus.VERIFYING.value:
            return None
        if current.lease_expires_at is not None and as_utc(
            current.lease_expires_at
        ) > as_utc(now):
            return None
        current.lease_owner = worker_id
        current.lease_expires_at = now + lease_for
        current.heartbeat_at = now
        current.updated_at = now
        await session.flush()
        return verification_claim(row, current)


async def heartbeat_verification(
    sessions: async_sessionmaker[AsyncSession],
    resource_id: UUID,
    attempt: int,
    *,
    worker_id: str,
    stage: str,
    progress: int,
    now: datetime,
    lease_for: timedelta,
) -> bool:
    validate_heartbeat(attempt, worker_id, stage, progress, lease_for)
    async with sessions() as session, session.begin():
        row = await lock_document(session, resource_id)
        if row.status != ImportStatus.VERIFYING.value or row.attempt != attempt:
            return False
        current = await lock_attempt(session, row.id, attempt)
        if current.status != ImportStatus.VERIFYING.value or not owns(
            current, worker_id, now
        ):
            return False
        current.heartbeat_at = now
        current.lease_expires_at = now + lease_for
        current.updated_at = now
        await session.flush()
        return True


async def recover_expired_verifications(
    sessions: async_sessionmaker[AsyncSession], now: datetime, *, limit: int
) -> tuple[UUID, ...]:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    async with sessions() as session, session.begin():
        statement = (
            select(DocumentRow, DocumentImportAttemptRow)
            .join(
                DocumentImportAttemptRow,
                (DocumentImportAttemptRow.resource_id == DocumentRow.id)
                & (DocumentImportAttemptRow.attempt == DocumentRow.attempt),
            )
            .where(
                DocumentRow.status == ImportStatus.VERIFYING.value,
                DocumentImportAttemptRow.status == ImportStatus.VERIFYING.value,
                DocumentImportAttemptRow.lease_expires_at.is_not(None),
                DocumentImportAttemptRow.lease_expires_at <= now,
            )
            .order_by(
                DocumentImportAttemptRow.lease_expires_at,
                DocumentImportAttemptRow.resource_id,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        pairs = tuple((await session.execute(statement)).all())
        recovered: list[UUID] = []
        for row, current in pairs:
            clear_lease(current, current.heartbeat_at)
            current.updated_at = now
            session.add(
                OutboxEventRow(
                    id=uuid4(),
                    aggregate_type="document",
                    aggregate_id=row.id,
                    event_type=CONTENT_IMPORT_VERIFY_REQUESTED,
                    payload=import_verify_requested_payload(
                        row.id, ContentKind.SCREENPLAY, row.attempt, row.version
                    ),
                    available_at=now,
                    created_at=now,
                )
            )
            recovered.append(row.id)
        await session.flush()
        return tuple(recovered)
