from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.infrastructure.database import Base
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.postgres import isolated_postgres_engine


@pytest.fixture
async def postgres_engine() -> AsyncIterator[AsyncEngine]:
    async with isolated_postgres_engine() as engine:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield engine
