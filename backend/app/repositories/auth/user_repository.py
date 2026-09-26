"""SQLAlchemy profile and administrator user management repository."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AuthSessionRow, UserRow
from app.models.web_session import WebSessionRow
from app.repositories.auth.mapping import account_from_row
from app.services.auth.errors import DuplicateUsernameError, LastAdminError
from app.services.auth.models import AccountRecord, ManagedUserPage, UserRole
from app.services.quotas import UserQuota


class SqlAlchemyUserRepository:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        *,
        revoke_sessions: Callable[[UUID], Awaitable[None]] | None = None,
    ) -> None:
        self._sessions = sessions
        self._revoke_sessions = revoke_sessions

    async def get_avatar(self, account_id: UUID) -> bytes | None:
        async with self._sessions() as session:
            return await session.scalar(
                select(UserRow.avatar_data).where(
                    UserRow.id == account_id, UserRow.is_active.is_(True)
                )
            )

    async def set_avatar(
        self,
        *,
        account_id: UUID,
        data: bytes | None,
        version: UUID | None,
        now: datetime,
    ) -> AccountRecord | None:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(UserRow)
                .where(UserRow.id == account_id, UserRow.is_active.is_(True))
                .values(avatar_data=data, avatar_version=version, updated_at=now)
                .returning(UserRow)
            )
        return account_from_row(row) if row is not None else None

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
        quota: UserQuota | None,
        now: datetime,
    ) -> AccountRecord | None:
        values: dict[str, object] = {"updated_at": now}
        if role is not None:
            values["role"] = role.value
        if is_active is not None:
            values["is_active"] = is_active
        if quota is not None:
            values.update(
                quota_exempt=quota.exempt,
                quota_max_active_tasks=quota.max_active_per_owner,
                quota_daily_tasks=quota.daily_tasks,
                quota_daily_bytes=quota.daily_bytes,
                quota_storage_bytes=quota.storage_bytes,
                quota_daily_analysis_attempts=quota.daily_analysis_attempts,
            )
        should_revoke_sessions = False
        async with self._sessions.begin() as session:
            if role is UserRole.USER or is_active is False:
                active_admin_ids = (
                    await session.scalars(
                        select(UserRow.id)
                        .where(
                            UserRow.role == UserRole.ADMIN.value,
                            UserRow.is_active.is_(True),
                        )
                        .order_by(UserRow.id)
                        .with_for_update()
                    )
                ).all()
                if account_id in active_admin_ids and len(active_admin_ids) == 1:
                    raise LastAdminError
            row = await session.scalar(
                update(UserRow)
                .where(UserRow.id == account_id)
                .values(**values)
                .returning(UserRow)
            )
            if row is not None and is_active is False:
                await session.execute(
                    update(WebSessionRow)
                    .where(
                        WebSessionRow.user_id == account_id,
                        WebSessionRow.revoked_at.is_(None),
                    )
                    .values(revoked_at=now)
                )
                await session.execute(
                    delete(AuthSessionRow).where(AuthSessionRow.user_id == account_id)
                )
                should_revoke_sessions = True
        if should_revoke_sessions and self._revoke_sessions is not None:
            await self._revoke_sessions(account_id)
        return account_from_row(row) if row is not None else None

    async def delete_account(self, *, account_id: UUID) -> bool:
        async with self._sessions.begin() as session:
            await session.execute(
                delete(AuthSessionRow).where(AuthSessionRow.user_id == account_id)
            )
            result = await session.execute(
                delete(UserRow).where(UserRow.id == account_id).returning(UserRow.id)
            )
            deleted = result.scalar_one_or_none() is not None
        if deleted and self._revoke_sessions is not None:
            await self._revoke_sessions(account_id)
        return deleted
