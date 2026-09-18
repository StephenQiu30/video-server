"""Shared SQLAlchemy metadata and PostgreSQL column types."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

JSON_DOCUMENT = JSONB()


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize application timestamps at repository boundaries."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base shared by database adapters."""


def create_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    if make_url(database_url).drivername != "postgresql+asyncpg":
        raise ValueError("DATABASE_URL must use postgresql+asyncpg")
    return create_async_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
