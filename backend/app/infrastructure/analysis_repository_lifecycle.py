"""Lease-bound claim, progress and owner cancellation operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.application.analysis import (
    AnalysisJobSnapshot,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.infrastructure.analysis_repository_create import AnalysisCreationRepository
from app.infrastructure.analysis_repository_mapping import analysis_job_snapshot
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import AnalysisJobRow

STAGE_RANKS = {
    "preparing": 1,
    "analyzing": 2,
    "validating": 3,
}


class AnalysisLifecycleRepository(AnalysisCreationRepository):
    async def claim_job(
        self,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_for: timedelta,
    ) -> AnalysisJobSnapshot | None:
        if lease_for <= timedelta(0):
            raise ValueError("lease duration must be positive")
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(AnalysisJobRow)
                .where(AnalysisJobRow.id == job_id)
                .with_for_update()
            )
            if (
                row is None
                or row.status != "queued"
                or row.attempt >= row.max_attempts
                or row.retry_at is not None
            ):
                return None
            row.status = "running"
            row.stage = "preparing"
            row.stage_rank = 1
            row.progress = 0
            row.attempt += 1
            row.version += 1
            row.lease_owner = worker_id
            row.lease_expires_at = now + lease_for
            row.heartbeat_at = now
            row.started_at = row.started_at or now
            row.error_code = None
            row.error_message = None
            row.updated_at = now
            await session.flush()
            return analysis_job_snapshot(row)

    async def heartbeat(
        self,
        job_id: UUID,
        worker_id: str,
        attempt: int,
        *,
        stage: str,
        progress: int,
        now: datetime,
        lease_for: timedelta,
    ) -> bool:
        requested_rank = STAGE_RANKS.get(stage)
        if requested_rank is None or not 0 <= progress <= 100:
            raise ValueError("invalid analysis stage or progress")
        if lease_for <= timedelta(0):
            raise ValueError("lease duration must be positive")
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(AnalysisJobRow)
                .where(AnalysisJobRow.id == job_id)
                .with_for_update()
            )
            if row is None or not self._owns(row, worker_id, attempt, now):
                return False
            if requested_rank not in {row.stage_rank, row.stage_rank + 1}:
                raise PersistenceConflict("analysis stage must advance linearly")
            if progress < row.progress:
                raise PersistenceConflict("analysis progress cannot decrease")
            row.stage = stage
            row.stage_rank = requested_rank
            row.progress = progress
            row.version += 1
            row.heartbeat_at = now
            row.lease_expires_at = now + lease_for
            row.updated_at = now
            await session.flush()
            return True

    async def cancel_job(
        self, job_id: UUID, owner_hash: str, now: datetime
    ) -> AnalysisJobSnapshot:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(AnalysisJobRow)
                .where(
                    AnalysisJobRow.id == job_id,
                    AnalysisJobRow.owner_hash == owner_hash,
                )
                .with_for_update()
            )
            if row is None:
                raise PersistenceNotFound("analysis job does not exist")
            if row.status == "cancelled":
                return analysis_job_snapshot(row)
            if row.status not in {"queued", "running", "retry_wait"}:
                raise PersistenceConflict("terminal analysis cannot be cancelled")
            row.status = "cancelled"
            row.stage = None
            row.stage_rank = 0
            row.version += 1
            row.cancel_requested_at = now
            row.finished_at = now
            row.retry_at = None
            row.error_code = "cancelled"
            row.error_message = None
            row.lease_owner = None
            row.lease_expires_at = None
            row.heartbeat_at = None
            row.updated_at = now
            await self.release_lock(session, row.id)
            await session.flush()
            return analysis_job_snapshot(row)

    @staticmethod
    def _owns(row: AnalysisJobRow, worker_id: str, attempt: int, now: datetime) -> bool:
        return (
            row.status == "running"
            and row.lease_owner == worker_id
            and row.attempt == attempt
            and row.lease_expires_at is not None
            and as_utc(row.lease_expires_at) > as_utc(now)
        )
