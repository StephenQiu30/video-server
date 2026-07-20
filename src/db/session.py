"""Async SQLAlchemy engine/session lifecycle shared by API, Worker and tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def session_context(
    settings: Settings | None = None,
) -> AsyncIterator[AsyncSession]:
    """Yield a transaction-scoped session and roll back unhandled failures."""
    engine = (
        get_engine()
        if settings is None
        else create_async_engine(settings.database_url, pool_pre_ping=True)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            if settings is not None:
                await engine.dispose()


async def dispose_engine() -> None:
    """Close pooled connections during process shutdown."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
