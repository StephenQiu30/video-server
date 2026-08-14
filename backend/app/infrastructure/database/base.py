"""Shared SQLAlchemy metadata and PostgreSQL column types."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import JSONB
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
