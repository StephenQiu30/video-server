"""SQLAlchemy authentication repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.auth import AccountRecord, CurrentUser, UserRole
from app.application.auth.errors import DuplicateEmailError, DuplicateUsernameError
from app.infrastructure.auth_mapping import account_from_row, current_user_from_row
from app.infrastructure.database.models import AuthSessionRow, UserRow


class SqlAlchemyAuthRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create_account(
        self,
        *,
        account_id: UUID,
        username: str,
        normalized_username: str,
        email: str,
        password_hash: str,
        role: UserRole,
        now: datetime,
    ) -> AccountRecord:
        row = UserRow(
            id=account_id,
            username=username,
            normalized_username=normalized_username,
            email=email,
            password_hash=password_hash,
            role=role.value,
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
                _raise_account_conflict(exc)
        return account_from_row(row)

    async def has_accounts(self) -> bool:
        async with self._sessions() as session:
            return bool(
                await session.scalar(select(exists().where(UserRow.id.is_not(None))))
            )

    async def find_account_by_email(self, email: str) -> AccountRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(select(UserRow).where(UserRow.email == email))
        return account_from_row(row) if row is not None else None

    async def find_account_by_id(self, account_id: UUID) -> AccountRecord | None:
        async with self._sessions() as session:
            row = await session.get(UserRow, account_id)
        return account_from_row(row) if row is not None else None

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
        return current_user_from_row(row) if row is not None else None

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


def _raise_account_conflict(error: IntegrityError) -> None:
    detail = str(error.orig).casefold()
    if "username" in detail:
        raise DuplicateUsernameError from error
    raise DuplicateEmailError from error
