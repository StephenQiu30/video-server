"""Download-capable processes must refuse work before consuming messages."""

from __future__ import annotations

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from app.core.runtime import ApiRuntime, ApiServices
from app.workers.download.main import DownloadWorkerRuntime, _serve
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def _drop_execution_column(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text("ALTER TABLE download_jobs DROP COLUMN execution_access_context")
        )


async def test_api_refuses_to_start_realtime_before_schema_migration(
    postgres_engine: AsyncEngine,
) -> None:
    await _drop_execution_column(postgres_engine)
    realtime = AsyncMock()
    runtime = ApiRuntime(
        services=ApiServices(),
        engine=postgres_engine,
        runner=cast(Any, None),
        auth_session_store=cast(Any, None),
        realtime_consumer=cast(Any, realtime),
    )

    with pytest.raises(RuntimeError, match="download execution schema"):
        await runtime.start()

    realtime.start.assert_not_awaited()


async def test_download_worker_refuses_to_consume_before_schema_migration(
    postgres_engine: AsyncEngine,
) -> None:
    await _drop_execution_column(postgres_engine)
    consumer = AsyncMock()
    intent_consumer = AsyncMock()
    sweeper = AsyncMock()
    runtime = DownloadWorkerRuntime(
        consumer=cast(Any, consumer),
        intent_consumer=cast(Any, intent_consumer),
        sweeper=cast(Any, sweeper),
        storage=cast(Any, None),
        runner=cast(Any, None),
        engine=postgres_engine,
    )

    with pytest.raises(RuntimeError, match="download execution schema"):
        await _serve(runtime, asyncio.Event())

    consumer.run.assert_not_awaited()
    intent_consumer.run.assert_not_awaited()
    sweeper.run.assert_not_awaited()
