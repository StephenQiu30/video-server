"""SQLAlchemy authentication repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.auth import AccountRecord, CurrentUser
from app.application.auth.errors import DuplicateEmailError
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import AuthSessionRow, UserRow


class SqlAlchemyAuthRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create_account(
        self,
        *,
        account_id: UUID,
        email: str,
        password_hash: str,
        now: datetime,
    ) -> AccountRecord:
        row = UserRow(
            id=account_id,
            email=email,
            password_hash=password_hash,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        async with self._sessions() as session:
            session.add(row)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise DuplicateEmailError from exc
        return _account(row)

    async def find_account_by_email(self, email: str) -> AccountRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(select(UserRow).where(UserRow.email == email))
        return _account(row) if row is not None else None

    async def find_account_by_id(self, account_id: UUID) -> AccountRecord | None:
        async with self._sessions() as session:
            row = await session.get(UserRow, account_id)
        return _account(row) if row is not None else None

    async def update_password_hash(
        self, account_id: UUID, password_hash: str, now: datetime
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(UserRow)
                .where(UserRow.id == account_id)
                .values(password_hash=password_hash, updated_at=now)
            )

    async def create_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(AuthSessionRow).where(AuthSessionRow.expires_at <= now)
            )
            session.add(
                AuthSessionRow(
                    id=session_id,
                    user_id=user_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                    created_at=now,
                )
            )

    async def find_user_by_session(
        self, token_hash: str, now: datetime
    ) -> CurrentUser | None:
        query = (
            select(UserRow)
            .join(AuthSessionRow, AuthSessionRow.user_id == UserRow.id)
            .where(
                AuthSessionRow.token_hash == token_hash,
                AuthSessionRow.expires_at > now,
                UserRow.is_active.is_(True),
            )
        )
        async with self._sessions() as session:
            row = await session.scalar(query)
        return _current_user(row) if row is not None else None

    async def delete_session(self, token_hash: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(AuthSessionRow).where(AuthSessionRow.token_hash == token_hash)
            )

    async def replace_session(
        self,
        *,
        previous_token_hash: str,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> bool:
        async with self._sessions.begin() as session:
            deleted_id = await session.scalar(
                delete(AuthSessionRow)
                .where(
                    AuthSessionRow.token_hash == previous_token_hash,
                    AuthSessionRow.user_id == user_id,
                    AuthSessionRow.expires_at > now,
                )
                .returning(AuthSessionRow.id)
            )
            if deleted_id is None:
                return False
            session.add(
                AuthSessionRow(
                    id=session_id,
                    user_id=user_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                    created_at=now,
                )
            )
        return True


def _account(row: UserRow) -> AccountRecord:
    return AccountRecord(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        is_active=row.is_active,
        created_at=as_utc(row.created_at),
    )


def _current_user(row: UserRow) -> CurrentUser:
    return CurrentUser(id=row.id, email=row.email, created_at=as_utc(row.created_at))
