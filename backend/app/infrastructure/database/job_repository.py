"""Transactional job creation, reads and lease acquisition."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .contracts import DownloadCreate, JobCreateResult, JobSnapshot
from .errors import (
    IdempotencyConflict,
    RepositoryConflict,
    RepositoryNotFound,
)
from .mapping import job_snapshot
from .media_repository import MediaRepository
from .models import (
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
    OutboxEventRow,
)


class JobRepository(MediaRepository):
    async def create_job(
        self, command: DownloadCreate, *, now: datetime
    ) -> JobCreateResult:
        async with self._sessions() as session:
            try:
                async with session.begin():
                    existing = await session.scalar(self._idempotency_query(command))
                    if existing is not None:
                        return self._idempotent_result(existing, command)
                    await self._validate_source(session, command, now)
                    row = DownloadJobRow(
                        id=command.id,
                        source_kind=command.source_kind,
                        inspection_id=command.inspection_id,
                        format_id=command.format_id,
                        owner_hash=command.owner_hash,
                        idempotency_key=command.idempotency_key,
                        request_fingerprint=command.request_fingerprint,
                        semantic_plan=command.semantic_plan,
                        max_attempts=command.max_attempts,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                    session.add(self._requested_event(row, now))
                    await session.flush()
                    result = JobCreateResult(job_snapshot(row), created=True)
                return result
            except IntegrityError as exc:
                await session.rollback()
                existing = await session.scalar(self._idempotency_query(command))
                if existing is None:
                    raise
                try:
                    return self._idempotent_result(existing, command)
                except IdempotencyConflict as conflict:
                    raise conflict from exc

    async def get_job(self, job_id: UUID) -> JobSnapshot:
        async with self._sessions() as session:
            row = await session.get(DownloadJobRow, job_id)
            if row is None:
                raise RepositoryNotFound("download job does not exist")
            return job_snapshot(row)

    async def claim_job(
        self,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_for: timedelta,
    ) -> JobSnapshot | None:
        statement = (
            update(DownloadJobRow)
            .where(
                DownloadJobRow.id == job_id,
                DownloadJobRow.source_kind == "remote_provider",
                DownloadJobRow.status == "queued",
                DownloadJobRow.attempt < DownloadJobRow.max_attempts,
                DownloadJobRow.retry_at.is_(None),
            )
            .values(
                status="running",
                stage="revalidating",
                stage_rank=1,
                attempt=DownloadJobRow.attempt + 1,
                version=DownloadJobRow.version + 1,
                lease_owner=worker_id,
                lease_expires_at=now + lease_for,
                heartbeat_at=now,
                started_at=func.coalesce(DownloadJobRow.started_at, now),
                retry_at=None,
                error_code=None,
                error_message=None,
                updated_at=now,
            )
            .returning(DownloadJobRow)
        )
        async with self._sessions() as session, session.begin():
            return_row = (await session.execute(statement)).scalar_one_or_none()
            return None if return_row is None else job_snapshot(return_row)

    @staticmethod
    def _idempotency_query(
        command: DownloadCreate,
    ) -> Select[tuple[DownloadJobRow]]:
        return select(DownloadJobRow).where(
            DownloadJobRow.owner_hash == command.owner_hash,
            DownloadJobRow.idempotency_key == command.idempotency_key,
        )

    @staticmethod
    def _idempotent_result(
        row: DownloadJobRow, command: DownloadCreate
    ) -> JobCreateResult:
        if row.request_fingerprint != command.request_fingerprint:
            raise IdempotencyConflict("download idempotency key already used")
        return JobCreateResult(job_snapshot(row), created=False)

    @staticmethod
    def _requested_event(row: DownloadJobRow, now: datetime) -> OutboxEventRow:
        return OutboxEventRow(
            id=uuid4(),
            aggregate_type="download_job",
            aggregate_id=row.id,
            event_type="download.requested",
            payload={
                "job_id": str(row.id),
                "attempt": row.attempt or 0,
                "version": row.version or 0,
            },
            available_at=now,
            created_at=now,
        )

    @staticmethod
    async def _validate_source(
        session: AsyncSession, command: DownloadCreate, now: datetime
    ) -> None:
        if command.source_kind != "remote_provider":
            raise RepositoryConflict("download source kind is not remotely inspectable")
        if command.inspection_id is None or command.format_id is None:
            raise RepositoryConflict("remote download source is incomplete")
        source_filters = [
            MediaInspectionRow.id == command.inspection_id,
            MediaInspectionRow.owner_hash == command.owner_hash,
            MediaFormatRow.id == command.format_id,
        ]
        if not command.allow_expired_source:
            # Explicit retries may reuse an expired snapshot reference. The
            # worker re-inspects the provider before it downloads any bytes.
            source_filters.extend(
                (
                    MediaInspectionRow.expires_at > now,
                    MediaFormatRow.expires_at > now,
                )
            )
        selected = (
            await session.execute(
                select(MediaInspectionRow, MediaFormatRow)
                .join(
                    MediaFormatRow,
                    MediaFormatRow.inspection_id == MediaInspectionRow.id,
                )
                .where(*source_filters)
            )
        ).one_or_none()
        if selected is None:
            raise RepositoryNotFound("inspection or format does not exist or expired")
        _, selected_format = selected
        if selected_format.semantic_plan != command.semantic_plan:
            raise RepositoryConflict("semantic plan differs from selected format")
