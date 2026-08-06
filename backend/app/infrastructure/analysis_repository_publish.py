"""Atomic strict-result persistence and successful analysis transition."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.application.analysis import (
    AnalysisJobSnapshot,
    AnalysisPublish,
    PersistenceConflict,
    PersistenceNotFound,
)
from app.infrastructure.analysis_repository_mapping import analysis_job_snapshot
from app.infrastructure.analysis_repository_recovery import AnalysisRecoveryRepository
from app.infrastructure.analysis_repository_serialization import (
    analysis_result_document,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import AnalysisJobRow, AnalysisResultRow


class AnalysisPublishRepository(AnalysisRecoveryRepository):
    async def publish_result(self, command: AnalysisPublish) -> AnalysisJobSnapshot:
        document = analysis_result_document(command.result)
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(AnalysisJobRow)
                .where(AnalysisJobRow.id == command.job_id)
                .with_for_update()
            )
            if row is None:
                raise PersistenceNotFound("analysis job does not exist")
            if row.status == "succeeded":
                stored = await session.scalar(
                    select(AnalysisResultRow).where(AnalysisResultRow.job_id == row.id)
                )
                if stored is None or stored.result_json != document:
                    raise PersistenceConflict("analysis result replay differs")
                return analysis_job_snapshot(row)
            if (
                row.status != "running"
                or row.stage != "validating"
                or row.lease_owner != command.lease_owner
                or row.lease_expires_at is None
                or as_utc(row.lease_expires_at) <= as_utc(command.now)
                or row.version != command.expected_version
            ):
                raise PersistenceConflict("analysis publish lease or version lost")
            if (
                row.schema_version != command.result.schema_version
                or row.output_language != command.result.language
            ):
                raise PersistenceConflict("analysis result contract differs from job")
            session.add(
                AnalysisResultRow(
                    id=uuid4(),
                    job_id=row.id,
                    input_sha256=row.input_sha256,
                    schema_version=row.schema_version,
                    language=row.output_language,
                    result_json=document,
                    created_at=command.now,
                )
            )
            row.status = "succeeded"
            row.stage = None
            row.stage_rank = 0
            row.progress = 100
            row.version += 1
            row.finished_at = command.now
            row.error_code = None
            row.error_message = None
            row.lease_owner = None
            row.lease_expires_at = None
            row.heartbeat_at = None
            row.updated_at = command.now
            await self.release_lock(session, row.id)
            await session.flush()
            return analysis_job_snapshot(row)
