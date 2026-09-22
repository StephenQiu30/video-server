"""PostgreSQL owns browser validity, activity and terminal revocation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.auth import UserRow
from app.models.web_session import WebSessionRow
from app.repositories.auth.mapping import current_user_from_row
from app.services.auth.errors import SessionStoreUnavailable
from app.services.auth.models import CurrentUser


class WebSessionRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[AsyncSession]:
        try:
            async with self._sessions.begin() as session:
                yield session
        except SQLAlchemyError as exc:
            raise SessionStoreUnavailable from exc

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        previous_hash: str | None,
        now: datetime,
        idle_expires_at: datetime,
        absolute_expires_at: datetime,
    ) -> CurrentUser | None:
        async with self._transaction() as session:
            # Same account lock as administrative changes: a late login cannot
            # create a live session after account deactivation commits.
            user = await session.scalar(
                select(UserRow).where(UserRow.id == user_id).with_for_update()
            )
            if user is None or not user.is_active:
                return None
            if previous_hash is not None:
                await session.execute(
                    update(WebSessionRow)
                    .where(
                        WebSessionRow.token_hash == previous_hash,
                        WebSessionRow.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )
            session.add(
                WebSessionRow(
                    user_id=user_id,
                    token_hash=token_hash,
                    created_at=now,
                    last_seen_at=now,
                    idle_expires_at=idle_expires_at,
                    absolute_expires_at=absolute_expires_at,
                )
            )
            # Bounded opportunistic GC; expiry already denies access regardless
            # of cleanup. Retain terminal evidence through absolute expiry + 1d.
            expired = (
                select(WebSessionRow.id)
                .where(WebSessionRow.absolute_expires_at < now - timedelta(days=1))
                .order_by(WebSessionRow.absolute_expires_at)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
            await session.execute(
                delete(WebSessionRow).where(WebSessionRow.id.in_(expired))
            )
            return current_user_from_row(user)

    async def current_user(
        self,
        token_hash: str,
        *,
        now: datetime,
        idle_ttl: timedelta,
        touch: bool,
    ) -> CurrentUser | None:
        async with self._transaction() as session:
            record = (
                await session.execute(
                    select(WebSessionRow, UserRow)
                    .join(UserRow, UserRow.id == WebSessionRow.user_id)
                    .where(
                        WebSessionRow.token_hash == token_hash,
                        WebSessionRow.revoked_at.is_(None),
                        WebSessionRow.idle_expires_at > now,
                        WebSessionRow.absolute_expires_at > now,
                        UserRow.is_active.is_(True),
                    )
                )
            ).one_or_none()
            if record is None:
                return None
            row, user = record
            if touch and row.last_seen_at <= now - timedelta(minutes=1):
                # Competing requests update at most once per minute. A revoke
                # or expiry that won the race cannot be undone by this write.
                await session.execute(
                    update(WebSessionRow)
                    .where(
                        WebSessionRow.id == row.id,
                        WebSessionRow.revoked_at.is_(None),
                        WebSessionRow.last_seen_at == row.last_seen_at,
                        WebSessionRow.idle_expires_at > now,
                        WebSessionRow.absolute_expires_at > now,
                    )
                    .values(
                        last_seen_at=now,
                        idle_expires_at=min(now + idle_ttl, row.absolute_expires_at),
                    )
                )
            return current_user_from_row(user)

    async def revoke(self, token_hash: str, *, now: datetime) -> UUID | None:
        async with self._transaction() as session:
            return await session.scalar(
                update(WebSessionRow)
                .where(
                    WebSessionRow.token_hash == token_hash,
                    WebSessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=now)
                .returning(WebSessionRow.user_id)
            )
