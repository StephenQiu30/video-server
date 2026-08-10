from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from app.infrastructure.database.models import DlqReplayRow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class ReplayAudit:
    id: UUID
    replay_event_id: UUID
    status: str
    created_at: datetime


class DlqReplayRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get_or_create(
        self,
        *,
        source_queue: str,
        original_event_id: UUID,
        replay_count: int,
        actor: str,
        reason: str,
        now: datetime,
    ) -> ReplayAudit:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(DlqReplayRow)
                .where(
                    DlqReplayRow.source_queue == source_queue,
                    DlqReplayRow.original_event_id == original_event_id,
                    DlqReplayRow.replay_count == replay_count,
                )
                .with_for_update()
            )
            if row is None:
                row = DlqReplayRow(
                    id=uuid4(),
                    source_queue=source_queue,
                    original_event_id=original_event_id,
                    replay_event_id=uuid4(),
                    replay_count=replay_count,
                    actor=actor,
                    reason=reason,
                    status="pending",
                    created_at=now,
                )
                session.add(row)
                await session.flush()
            return ReplayAudit(row.id, row.replay_event_id, row.status, row.created_at)

    async def mark_published(self, audit_id: UUID, now: datetime) -> None:
        await self._finish(audit_id, "published", None, now)

    async def mark_failed(self, audit_id: UUID, code: str, now: datetime) -> None:
        await self._finish(audit_id, "failed", code[:128], now)

    async def _finish(
        self, audit_id: UUID, status: str, error_code: str | None, now: datetime
    ) -> None:
        async with self._sessions() as session, session.begin():
            row = await session.get(DlqReplayRow, audit_id, with_for_update=True)
            if row is None:
                raise RuntimeError("DLQ replay audit disappeared")
            row.status = status
            row.error_code = error_code
            row.completed_at = now
