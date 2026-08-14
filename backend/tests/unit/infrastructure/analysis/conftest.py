from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


@dataclass(frozen=True, slots=True)
class AnalysisDatabase:
    sessions: async_sessionmaker[AsyncSession]
    repository: SqlAlchemyAnalysisRepository


@pytest.fixture
async def analysis_db(postgres_engine: AsyncEngine) -> AsyncIterator[AnalysisDatabase]:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    yield AnalysisDatabase(sessions, SqlAlchemyAnalysisRepository(sessions))
