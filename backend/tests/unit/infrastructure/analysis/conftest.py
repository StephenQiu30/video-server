from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database import Base
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True, slots=True)
class AnalysisDatabase:
    sessions: async_sessionmaker[AsyncSession]
    repository: SqlAlchemyAnalysisRepository


@pytest.fixture
async def analysis_db() -> AsyncIterator[AnalysisDatabase]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    yield AnalysisDatabase(sessions, SqlAlchemyAnalysisRepository(sessions))
    await engine.dispose()
