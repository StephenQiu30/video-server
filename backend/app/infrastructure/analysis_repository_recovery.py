"""Retry, terminal failure and bounded stale analysis recovery."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select

from app.application.analysis import AnalysisJobSnapshot, PersistenceNotFound
from app.infrastructure.analysis_repository_lifecycle import (
    AnalysisLifecycleRepository,
)
from app.infrastructure.analysis_repository_mapping import analysis_job_snapshot
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import AnalysisJobRow


def stale_analyses_statement(
    now: datetime, limit: int
) -> Select[tuple[AnalysisJobRow]]:
    return (
        select(AnalysisJobRow)
        .where(
            AnalysisJobRow.status == "running",
            AnalysisJobRow.lease_expires_at <= now,
        )
        .order_by(AnalysisJobRow.lease_expires_at, AnalysisJobRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def stale_queued_analyses_statement(
    stale_before: datetime, limit: int
) -> Select[tuple[AnalysisJobRow]]:
    return (
        select(AnalysisJobRow)
        .where(
            AnalysisJobRow.status == "queued",
            AnalysisJobRow.updated_at <= stale_before,
        )
        .order_by(AnalysisJobRow.updated_at, AnalysisJobRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def ready_analysis_retries_statement(
    now: datetime, limit: int
) -> Select[tuple[AnalysisJobRow]]:
    return (
        select(AnalysisJobRow)
        .where(
            AnalysisJobRow.status == "retry_wait",
            AnalysisJobRow.retry_at <= now,
        )
        .order_by(AnalysisJobRow.retry_at, AnalysisJobRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


class AnalysisRecoveryRepository(AnalysisLifecycleRepository):
    async def recover_stale_queued(
        self, now: datetime, stale_before: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]:
        _valid_limit(limit)
        if stale_before >= now:
            raise ValueError("stale_before must be before now")
        async with self._sessions() as session, session.begin():
            rows = tuple(
                (
                    await session.scalars(
                        stale_queued_analyses_statement(stale_before, limit)
                    )
                ).all()
            )
            for row in rows:
                run = await self.active_run(session, row, for_update=True)
                session.add(
                    self.requested_event(row, run, uuid4(), "analysis.requested", now)
                )
                row.updated_at = now
            await session.flush()
            return tuple(row.id for row in rows)

    async def complete_failure(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        now: datetime,
        retry_at: datetime | None = None,
    ) -> AnalysisJobSnapshot:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(AnalysisJobRow)
                .where(AnalysisJobRow.id == job_id)
                .with_for_update()
            )
            if row is None:
                raise PersistenceNotFound("analysis job does not exist")
            run = await self.active_run(session, row, for_update=True)
            self.require_lease(row, worker_id, attempt, now)
            should_retry = retryable and row.attempt < row.max_attempts
            if should_retry and (retry_at is None or as_utc(retry_at) <= as_utc(now)):
                raise ValueError("retry_at must be in the future")
            row.status = "retry_wait" if should_retry else "failed"
            row.stage = None
            row.stage_rank = 0
            row.version += 1
            row.retry_at = retry_at if should_retry else None
            row.finished_at = None if should_retry else now
            row.error_code = error_code
            row.error_message = error_message[:512]
            row.lease_owner = None
            row.lease_expires_at = None
            row.heartbeat_at = None
            row.updated_at = now
            self.sync_run(row, run)
            if not should_retry:
                await self.release_lock(session, row.id)
            await session.flush()
            return analysis_job_snapshot(row)

    async def reclaim_stale(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]:
        _valid_limit(limit)
        async with self._sessions() as session, session.begin():
            rows = tuple(
                (await session.scalars(stale_analyses_statement(now, limit))).all()
            )
            for row in rows:
                run = await self.active_run(session, row, for_update=True)
                can_retry = row.attempt < row.max_attempts
                row.status = "retry_wait" if can_retry else "failed"
                row.stage = None
                row.stage_rank = 0
                row.version += 1
                row.retry_at = now if can_retry else None
                row.finished_at = None if can_retry else now
                row.error_code = "worker_lost"
                row.error_message = "analysis worker lease expired"
                row.lease_owner = None
                row.lease_expires_at = None
                row.heartbeat_at = None
                row.updated_at = now
                self.sync_run(row, run)
                if not can_retry:
                    await self.release_lock(session, row.id)
            await session.flush()
            return tuple(row.id for row in rows)

    async def release_ready_retries(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]:
        _valid_limit(limit)
        async with self._sessions() as session, session.begin():
            rows = tuple(
                (
                    await session.scalars(ready_analysis_retries_statement(now, limit))
                ).all()
            )
            for row in rows:
                run = await self.active_run(session, row, for_update=True)
                row.status = "queued"
                row.retry_at = None
                row.version += 1
                row.updated_at = now
                self.sync_run(row, run)
                session.add(
                    self.requested_event(row, run, uuid4(), "analysis.requested", now)
                )
            await session.flush()
            return tuple(row.id for row in rows)


def _valid_limit(limit: int) -> None:
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
