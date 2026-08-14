from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.infrastructure.analysis_worker_registry import (
    SqlAlchemyAnalysisWorkerRegistry,
)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@pytest.mark.asyncio
async def test_worker_registry_requires_fresh_matching_capability(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    registry = SqlAlchemyAnalysisWorkerRegistry(
        sessions,
        expected_app_version="release-a",
        expected_message_schema_version=1,
        stale_after=timedelta(seconds=30),
    )
    now = datetime(2026, 8, 11, tzinfo=UTC)

    assert not await registry.is_available(now)
    await registry.heartbeat(
        "worker-a",
        app_version="release-a",
        message_schema_version=2,
        now=now,
    )
    assert not await registry.is_available(now)
    await registry.heartbeat(
        "worker-a",
        app_version="release-a",
        message_schema_version=1,
        now=now,
    )
    assert await registry.is_available(now + timedelta(seconds=30))
    assert not await registry.is_available(now + timedelta(seconds=31))
    await registry.unregister("worker-a")
    assert not await registry.is_available(now)
