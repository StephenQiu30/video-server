"""Common state held by concrete async repositories."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class RepositoryBase:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions
