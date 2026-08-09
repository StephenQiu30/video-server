"""SQLAlchemy profile and administrator user management repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.auth import AccountRecord, ManagedUserPage, UserRole
from app.application.auth.errors import DuplicateUsernameError
from app.infrastructure.auth_mapping import account_from_row
from app.infrastructure.database.models import AuthSessionRow, UserRow


class SqlAlchemyUserRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def update_username(
        self,
        *,
        account_id: UUID,
        username: str,
        normalized_username: str,
        now: datetime,
    ) -> AccountRecord | None:
        statement = (
            update(UserRow)
            .where(UserRow.id == account_id)
            .values(
                username=username,
                normalized_username=normalized_username,
                updated_at=now,
            )
            .returning(UserRow)
        )
        try:
            async with self._sessions.begin() as session:
                row = await session.scalar(statement)
        except IntegrityError as exc:
            raise DuplicateUsernameError from exc
        return account_from_row(row) if row is not None else None

    async def list_accounts(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: UserRole | None,
        is_active: bool | None,
    ) -> ManagedUserPage:
        filters = []
        if search:
            normalized = search.casefold()
            filters.append(
                or_(
                    UserRow.normalized_username.contains(normalized, autoescape=True),
                    func.lower(UserRow.email).contains(normalized, autoescape=True),
                )
            )
        if role is not None:
            filters.append(UserRow.role == role.value)
        if is_active is not None:
            filters.append(UserRow.is_active.is_(is_active))
        async with self._sessions() as session:
            total = await session.scalar(
                select(func.count()).select_from(UserRow).where(*filters)
            )
            rows = (
                await session.scalars(
                    select(UserRow)
                    .where(*filters)
                    .order_by(UserRow.created_at.desc(), UserRow.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        return ManagedUserPage(
            items=tuple(account_from_row(row).managed_view() for row in rows),
            page=page,
            page_size=page_size,
            total=total or 0,
        )

    async def update_account_access(
        self,
        *,
        account_id: UUID,
        role: UserRole | None,
        is_active: bool | None,
        now: datetime,
    ) -> AccountRecord | None:
        values: dict[str, object] = {"updated_at": now}
        if role is not None:
            values["role"] = role.value
        if is_active is not None:
            values["is_active"] = is_active
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(UserRow)
                .where(UserRow.id == account_id)
                .values(**values)
                .returning(UserRow)
            )
            if row is not None and is_active is False:
                await session.execute(
                    delete(AuthSessionRow).where(AuthSessionRow.user_id == account_id)
                )
        return account_from_row(row) if row is not None else None
