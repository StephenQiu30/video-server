"""CAS publication prevents stale maintainers from resurrecting revoked sources."""

from datetime import datetime

from sqlalchemy import func, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.provider_session_source import ProviderSessionSourceRow as Row
from app.services.provider_types import ProviderKey


class SourceRevisionConflict(Exception):
    """The caller must reread metadata and explicitly approve a newer publication."""


class ProviderSessionSources:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def read(self, provider: ProviderKey) -> Row | None:
        async with self._sessions() as session, session.begin():
            await session.execute(text("SET LOCAL statement_timeout = '3s'"))
            return await session.get(Row, provider.value)

    async def publish(
        self,
        provider: ProviderKey,
        *,
        expected_revision: int,
        ciphertext: bytes | None,
        valid_until: datetime | None,
    ) -> int:
        if expected_revision < 0 or (ciphertext is None) != (valid_until is None):
            raise ValueError("invalid source publication")
        revision = expected_revision + 1
        values = dict(
            provider_key=provider.value,
            revision=revision,
            ciphertext=ciphertext,
            valid_until=valid_until,
            updated_at=func.clock_timestamp(),
        )
        async with self._sessions() as session, session.begin():
            await session.execute(text("SET LOCAL statement_timeout = '3s'"))
            await session.execute(text("SET LOCAL lock_timeout = '1s'"))
            if expected_revision == 0:
                statement = (
                    insert(Row)
                    .values(**values)
                    .on_conflict_do_nothing()
                    .returning(Row.revision)
                )
                result = await session.scalar(statement)
            else:
                update_statement = (
                    update(Row)
                    .where(
                        Row.provider_key == provider.value,
                        Row.revision == expected_revision,
                    )
                    .values(**values)
                    .returning(Row.revision)
                )
                result = await session.scalar(update_statement)
            if result is None:
                raise SourceRevisionConflict("source revision changed")
            return result
