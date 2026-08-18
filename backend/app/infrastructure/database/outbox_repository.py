"""Claim and acknowledge transactional outbox events."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, or_, select

from .access_repository import AccessRepository
from .contracts import OutboxSnapshot
from .mapping import outbox_snapshot
from .models import OutboxEventRow
from .operational_counter import increment_counter


def outbox_claim_statement(now: datetime, limit: int) -> Select[tuple[OutboxEventRow]]:
    return (
        select(OutboxEventRow)
        .where(
            OutboxEventRow.published_at.is_(None),
            OutboxEventRow.available_at <= now,
            or_(
                OutboxEventRow.next_attempt_at.is_(None),
                OutboxEventRow.next_attempt_at <= now,
            ),
            or_(
                OutboxEventRow.lock_expires_at.is_(None),
                OutboxEventRow.lock_expires_at <= now,
            ),
        )
        .order_by(OutboxEventRow.created_at, OutboxEventRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


class SqlAlchemyDownloadRepository(AccessRepository):
    async def claim_outbox(
        self,
        publisher_id: str,
        now: datetime,
        lease_for: timedelta,
        *,
        limit: int = 100,
    ) -> tuple[OutboxSnapshot, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        statement = outbox_claim_statement(now, limit)
        async with self._sessions() as session, session.begin():
            rows = tuple((await session.scalars(statement)).all())
            for row in rows:
                row.lock_owner = publisher_id
                row.lock_expires_at = now + lease_for
                row.last_attempt_at = now
                row.publish_attempts += 1
            await session.flush()
            return tuple(outbox_snapshot(row) for row in rows)

    async def mark_outbox_published(
        self, event_id: UUID, publisher_id: str, now: datetime
    ) -> bool:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(OutboxEventRow)
                .where(OutboxEventRow.id == event_id)
                .with_for_update()
            )
            if (
                row is None
                or row.published_at is not None
                or row.lock_owner != publisher_id
            ):
                return False
            row.published_at = now
            row.lock_owner = None
            row.lock_expires_at = None
            row.last_error = None
            await increment_counter(session, "outbox_confirm", "ack")
            return True

    async def mark_outbox_failed(
        self,
        event_id: UUID,
        publisher_id: str,
        now: datetime,
        error: str,
        retry_at: datetime,
    ) -> bool:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(OutboxEventRow)
                .where(OutboxEventRow.id == event_id)
                .with_for_update()
            )
            if (
                row is None
                or row.published_at is not None
                or row.lock_owner != publisher_id
            ):
                return False
            row.last_error = error[:512]
            row.next_attempt_at = retry_at
            row.lock_owner = None
            row.lock_expires_at = None
            row.last_attempt_at = now
            await increment_counter(session, "outbox_confirm", "failed")
            return True
