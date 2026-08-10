"""Authorized bounded recovery reads for realtime task subscriptions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.models import TaskEventRow


class TaskEventStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def replay(
        self,
        owner_hash: str,
        task_type: str,
        task_id: UUID,
        after_version: int,
        *,
        limit: int = 100,
    ) -> tuple[dict[str, object], ...] | None:
        if task_type not in {"download", "analysis"} or not 0 <= after_version:
            return None
        async with self._sessions() as session:
            owner = await session.scalar(
                select(TaskEventRow.owner_hash)
                .where(
                    TaskEventRow.task_type == task_type,
                    TaskEventRow.task_id == task_id,
                )
                .order_by(TaskEventRow.version.desc())
                .limit(1)
            )
            if owner != owner_hash:
                return None
            events = tuple(
                (
                    await session.scalars(
                        select(TaskEventRow)
                        .where(
                            TaskEventRow.owner_hash == owner_hash,
                            TaskEventRow.task_type == task_type,
                            TaskEventRow.task_id == task_id,
                            TaskEventRow.version > after_version,
                        )
                        .order_by(TaskEventRow.version)
                        .limit(limit + 1)
                    )
                ).all()
            )
            if len(events) > limit:
                events = events[-1:]
            return tuple(
                {
                    "type": "task.updated",
                    "event_id": str(event.id),
                    **event.payload,
                }
                for event in events
            )
