"""Common state held by concrete async repositories."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.quotas import QuotaPolicy


class RepositoryBase:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        quota_policy: QuotaPolicy | None = None,
    ) -> None:
        self._sessions = sessions
        self._quota_policy = quota_policy or QuotaPolicy()
