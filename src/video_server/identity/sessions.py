"""PostgreSQL-backed opaque browser session strategy."""

from __future__ import annotations

from uuid import UUID

from fastapi_users import models
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users.authentication.strategy.db.adapter import AccessTokenDatabase

from video_server.identity.models import AccessToken

SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60


def build_database_strategy(
    database: AccessTokenDatabase[AccessToken],
) -> DatabaseStrategy[models.UserProtocol[UUID], UUID, AccessToken]:
    """Create the frozen seven-day absolute database session strategy."""

    return DatabaseStrategy(database, lifetime_seconds=SESSION_LIFETIME_SECONDS)
