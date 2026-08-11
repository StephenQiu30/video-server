from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.infrastructure.database import Base
from app.infrastructure.database.models import TaskEventRow
from app.infrastructure.task_event_store import TaskEventStore
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_replay_returns_latest_snapshot_when_gap_exceeds_limit() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    owner_hash = "a" * 64
    task_id = uuid4()
    now = datetime(2026, 8, 11, tzinfo=UTC)
    async with sessions() as session, session.begin():
        session.add_all(
            TaskEventRow(
                id=uuid4(),
                owner_hash=owner_hash,
                task_type="analysis",
                task_id=task_id,
                version=version,
                event_type="task.updated",
                payload={
                    "task_type": "analysis",
                    "task_id": str(task_id),
                    "version": version,
                    "status": "running",
                },
                occurred_at=now,
            )
            for version in range(1, 131)
        )

    replay = await TaskEventStore(sessions).replay(
        owner_hash, "analysis", task_id, 0, limit=100
    )

    assert replay is not None
    assert len(replay) == 1
    assert replay[0]["type"] == "task.snapshot"
    assert replay[0]["version"] == 130
    await engine.dispose()
