"""Lease-bound claim, progress and owner cancellation operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update

from app.application.analysis import (
    AnalysisJobSnapshot,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.infrastructure.analysis_repository_base import AnalysisRepositoryBase
from app.infrastructure.analysis_repository_mapping import analysis_job_snapshot
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import (
    AnalysisJobRow,
    AnalysisReportArtifactRow,
    AnalysisResultRow,
    ArtifactRow,
)
from app.infrastructure.database.operational_counter import increment_counter

STAGE_RANKS = {
    "preparing": 1,
    "analyzing": 2,
    "validating": 3,
}


class AnalysisLifecycleRepository(AnalysisRepositoryBase):
    async def get_latest_job_for_download(
        self, download_id: UUID, owner_hash: str
    ) -> AnalysisJobSnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AnalysisJobRow)
                .join(ArtifactRow, ArtifactRow.id == AnalysisJobRow.artifact_id)
                .where(
                    ArtifactRow.job_id == download_id,
                    AnalysisJobRow.owner_hash == owner_hash,
                    AnalysisJobRow.deleted_at.is_(None),
                )
                .order_by(AnalysisJobRow.created_at.desc())
                .limit(1)
            )
            return None if row is None else analysis_job_snapshot(row)

    async def get_latest_job_for_document(
        self, document_id: UUID, owner_hash: str
    ) -> AnalysisJobSnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(AnalysisJobRow)
                .where(
                    AnalysisJobRow.document_id == document_id,
                    AnalysisJobRow.owner_hash == owner_hash,
                    AnalysisJobRow.deleted_at.is_(None),
                )
                .order_by(AnalysisJobRow.created_at.desc(), AnalysisJobRow.id.desc())
                .limit(1)
            )
            return None if row is None else analysis_job_snapshot(row)

    async def delete_job(self, job_id: UUID, owner_hash: str, now: datetime) -> bool:
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
            if row.deleted_at is not None:
                return False
            run = await self.active_run(session, row, for_update=True)
            if row.status in {"queued", "running", "retry_wait"}:
                row.status = "cancelled"
                row.stage = None
                row.stage_rank = 0
                row.error_code = "cancelled"
                row.finished_at = now
                row.lease_owner = None
                row.lease_expires_at = None
                row.heartbeat_at = None
                row.version += 1
                self.sync_run(row, run)
                await self.release_lock(session, row.id)
            else:
                row.version += 1
            row.deleted_at = now
            row.updated_at = now
            report_ids = select(AnalysisResultRow.id).where(
                AnalysisResultRow.job_id == row.id
            )
            await session.execute(
                update(AnalysisResultRow)
                .where(AnalysisResultRow.job_id == row.id)
                .values(status="delete_pending")
            )
            await session.execute(
                update(AnalysisReportArtifactRow)
                .where(
                    AnalysisReportArtifactRow.report_id.in_(report_ids),
                    AnalysisReportArtifactRow.deleted_at.is_(None),
                )
                .values(status="delete_pending")
            )
            return True

    async def claim_job(
        self,
        job_id: UUID,
        run_id: UUID,
        run_no: int,
        expected_version: int,
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
                or row.active_run_id != run_id
                or row.current_run_no != run_no
                or row.version != expected_version
                or row.status != "queued"
                or row.attempt >= row.max_attempts
                or row.retry_at is not None
            ):
                await increment_counter(session, "claim_noop", "analysis")
                return None
            run = await self.active_run(session, row, for_update=True)
            if run.status != "queued" or run.run_no != row.current_run_no:
                await increment_counter(session, "claim_noop", "analysis")
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
            self.sync_run(row, run)
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
            run = await self.active_run(session, row, for_update=True)
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
            self.sync_run(row, run)
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
            run = await self.active_run(session, row, for_update=True)
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
            self.sync_run(row, run)
            report = await session.scalar(
                select(AnalysisResultRow)
                .where(AnalysisResultRow.run_id == run.id)
                .with_for_update()
            )
            if report is not None and report.status in {"validated", "publish_failed"}:
                report.status = "delete_pending"
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
