"""Retention-safe artifact deletion with database row locking."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select

from .access_repository import AccessRepository
from .contracts import ArtifactPurgeResult
from .models import AnalysisArtifactLockRow, ArtifactRow

ArtifactDelete = Callable[[str], Awaitable[None]]


def expired_artifact_statement(
    now: datetime, limit: int, excluded: tuple[UUID, ...] = ()
) -> Select[tuple[ArtifactRow]]:
    lock_exists = select(AnalysisArtifactLockRow.job_id).where(
        AnalysisArtifactLockRow.artifact_id == ArtifactRow.id
    )
    statement = (
        select(ArtifactRow)
        .where(
            ArtifactRow.deleted_at.is_(None),
            ArtifactRow.expires_at <= now,
            ~lock_exists.exists(),
        )
        .order_by(ArtifactRow.expires_at, ArtifactRow.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    if excluded:
        statement = statement.where(~ArtifactRow.id.in_(excluded))
    return statement


class ArtifactLifecycleRepository(AccessRepository):
    async def purge_expired_artifacts(
        self,
        now: datetime,
        delete: ArtifactDelete,
        *,
        limit: int = 50,
    ) -> ArtifactPurgeResult:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        deleted = 0
        failed = 0
        excluded: list[UUID] = []
        for _ in range(limit):
            async with self._sessions() as session, session.begin():
                row = await session.scalar(
                    expired_artifact_statement(now, 1, tuple(excluded))
                )
                if row is None:
                    break
                try:
                    await delete(row.object_key)
                except Exception:
                    failed += 1
                    excluded.append(row.id)
                    continue
                row.deleted_at = now
                await session.flush()
                deleted += 1
        return ArtifactPurgeResult(deleted=deleted, failed=failed)
