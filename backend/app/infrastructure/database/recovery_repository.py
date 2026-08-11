"""Bounded stale-lease reclamation for crashed workers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select

from .completion_repository import CompletionRepository
from .models import DownloadJobRow


def stale_jobs_statement(now: datetime, limit: int) -> Select[tuple[DownloadJobRow]]:
    return (
        select(DownloadJobRow)
        .where(
            DownloadJobRow.status == "running",
            DownloadJobRow.lease_expires_at <= now,
        )
        .order_by(DownloadJobRow.lease_expires_at, DownloadJobRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def ready_retries_statement(now: datetime, limit: int) -> Select[tuple[DownloadJobRow]]:
    return (
        select(DownloadJobRow)
        .where(
            DownloadJobRow.status == "retry_wait",
            DownloadJobRow.retry_at <= now,
        )
        .order_by(DownloadJobRow.retry_at, DownloadJobRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def stale_queued_jobs_statement(
    stale_before: datetime, limit: int
) -> Select[tuple[DownloadJobRow]]:
    return (
        select(DownloadJobRow)
        .where(
            DownloadJobRow.status == "queued",
            DownloadJobRow.updated_at <= stale_before,
        )
        .order_by(DownloadJobRow.updated_at, DownloadJobRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


class RecoveryRepository(CompletionRepository):
    async def recover_stale_queued(
        self,
        now: datetime,
        stale_before: datetime,
        *,
        limit: int = 100,
    ) -> tuple[UUID, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        statement = stale_queued_jobs_statement(stale_before, limit)
        async with self._sessions() as session, session.begin():
            rows = tuple((await session.scalars(statement)).all())
            for row in rows:
                session.add(self._requested_event(row, now))
                # Throttle recovery publication while preserving job/version identity.
                row.updated_at = now
            await session.flush()
            return tuple(row.id for row in rows)

    async def reclaim_stale(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        statement = stale_jobs_statement(now, limit)
        async with self._sessions() as session, session.begin():
            rows = tuple((await session.scalars(statement)).all())
            for row in rows:
                can_retry = row.attempt < row.max_attempts
                row.status = "retry_wait" if can_retry else "failed"
                row.stage = None
                row.stage_rank = 0
                row.version += 1
                row.retry_at = now if can_retry else None
                row.finished_at = None if can_retry else now
                row.error_code = "worker_lost"
                row.error_message = "worker lease expired"
                row.lease_owner = None
                row.lease_expires_at = None
                row.updated_at = now
            await session.flush()
            return tuple(row.id for row in rows)

    async def release_ready_retries(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        statement = ready_retries_statement(now, limit)
        async with self._sessions() as session, session.begin():
            rows = tuple((await session.scalars(statement)).all())
            for row in rows:
                row.status = "queued"
                row.retry_at = None
                row.version += 1
                row.updated_at = now
                session.add(self._requested_event(row, now))
            await session.flush()
            return tuple(row.id for row in rows)
