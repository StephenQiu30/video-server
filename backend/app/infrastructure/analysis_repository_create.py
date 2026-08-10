"""Atomic analysis job, retention lock and outbox creation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analysis import (
    AnalysisCreate,
    AnalysisJobSaveResult,
    PersistenceConflict,
    PersistenceIdempotencyConflict,
    PersistenceNotFound,
)
from app.infrastructure.analysis_repository_base import AnalysisRepositoryBase
from app.infrastructure.analysis_repository_mapping import analysis_job_snapshot
from app.infrastructure.database.models import (
    AnalysisArtifactLockRow,
    AnalysisJobRow,
    ArtifactRow,
    DownloadJobRow,
)


class AnalysisCreationRepository(AnalysisRepositoryBase):
    async def create_job_and_enqueue(
        self, command: AnalysisCreate, *, now: datetime
    ) -> AnalysisJobSaveResult:
        if command.outbox_event_type != "analysis.requested":
            raise PersistenceConflict("invalid analysis outbox event type")
        async with self._sessions() as session:
            try:
                async with session.begin():
                    existing = await session.scalar(self._key_query(command))
                    if existing is not None:
                        return self._key_replay(existing, command)
                    await self._validate_source(session, command, now)
                    row = self._new_row(command, now)
                    session.add(row)
                    # The lock references analysis_jobs. Flush the parent first
                    # instead of relying on SQLAlchemy to infer an ORM dependency
                    # from UUID values alone (there is no relationship configured).
                    await session.flush((row,))
                    session.add(
                        AnalysisArtifactLockRow(
                            job_id=row.id,
                            artifact_id=row.artifact_id,
                            created_at=now,
                        )
                    )
                    session.add(
                        self.requested_event(
                            row,
                            command.outbox_event_id,
                            command.outbox_event_type,
                            now,
                        )
                    )
                    await session.flush()
                    result = AnalysisJobSaveResult(
                        analysis_job_snapshot(row), created=True
                    )
                return result
            except IntegrityError as exc:
                await session.rollback()
                existing = await session.scalar(self._key_query(command))
                if existing is not None:
                    return self._key_replay(existing, command)
                raise exc

    @staticmethod
    def _key_query(command: AnalysisCreate) -> Select[tuple[AnalysisJobRow]]:
        return select(AnalysisJobRow).where(
            AnalysisJobRow.owner_hash == command.owner_hash,
            AnalysisJobRow.idempotency_key == command.idempotency_key,
        )

    @staticmethod
    def _key_replay(
        row: AnalysisJobRow, command: AnalysisCreate
    ) -> AnalysisJobSaveResult:
        if row.request_fingerprint != command.request_fingerprint:
            raise PersistenceIdempotencyConflict("analysis idempotency key reused")
        return AnalysisJobSaveResult(analysis_job_snapshot(row), created=False)

    @staticmethod
    async def _validate_source(
        session: AsyncSession, command: AnalysisCreate, now: datetime
    ) -> None:
        source = (
            await session.execute(
                select(ArtifactRow, DownloadJobRow)
                .join(DownloadJobRow, DownloadJobRow.id == ArtifactRow.job_id)
                .where(
                    ArtifactRow.id == command.artifact_id,
                    ArtifactRow.deleted_at.is_(None),
                    ArtifactRow.expires_at > now,
                    DownloadJobRow.owner_hash == command.owner_hash,
                    DownloadJobRow.status == "succeeded",
                )
                .with_for_update()
            )
        ).one_or_none()
        if source is None:
            raise PersistenceNotFound("analysis artifact is unavailable")
        artifact, _ = source
        if artifact.sha256 != command.input_sha256:
            raise PersistenceConflict("analysis input SHA changed")

    @staticmethod
    def _new_row(command: AnalysisCreate, now: datetime) -> AnalysisJobRow:
        return AnalysisJobRow(
            id=command.id,
            artifact_id=command.artifact_id,
            owner_hash=command.owner_hash,
            idempotency_key=command.idempotency_key,
            request_fingerprint=command.request_fingerprint,
            input_sha256=command.input_sha256,
            skill_id=command.skill_id,
            skill_instructions=command.skill_instructions,
            output_language=command.output_language,
            custom_prompt=command.custom_prompt,
            max_attempts=command.max_attempts,
            created_at=now,
            updated_at=now,
        )
