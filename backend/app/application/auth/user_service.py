from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from .errors import AuthError, AuthErrorCode, DuplicateUsernameError
from .models import CurrentUser, ManagedUser, ManagedUserPage, UserRole
from .ports import UserRepository
from .usernames import normalize_username


class UserService:
    def __init__(
        self,
        *,
        repository: UserRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._now = now

    async def update_profile(self, user: CurrentUser, username: str) -> CurrentUser:
        try:
            display, normalized = normalize_username(username)
            account = await self._repository.update_username(
                account_id=user.id,
                username=display,
                normalized_username=normalized,
                now=self._now(),
            )
        except ValueError as exc:
            raise AuthError(AuthErrorCode.INVALID_USERNAME) from exc
        except DuplicateUsernameError as exc:
            raise AuthError(AuthErrorCode.USERNAME_ALREADY_REGISTERED) from exc
        if account is None or not account.is_active:
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        return account.public_view()

    async def list_users(
        self,
        actor: CurrentUser,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: UserRole | None,
        is_active: bool | None,
    ) -> ManagedUserPage:
        _require_admin(actor)
        return await self._repository.list_accounts(
            page=page,
            page_size=page_size,
            search=search.strip() if search and search.strip() else None,
            role=role,
            is_active=is_active,
        )

    async def update_access(
        self,
        actor: CurrentUser,
        account_id: UUID,
        *,
        role: UserRole | None,
        is_active: bool | None,
    ) -> ManagedUser:
        _require_admin(actor)
        if actor.id == account_id and (
            (role is not None and role is not UserRole.ADMIN) or is_active is False
        ):
            raise AuthError(AuthErrorCode.SELF_ADMIN_CHANGE)
        account = await self._repository.update_account_access(
            account_id=account_id,
            role=role,
            is_active=is_active,
            now=self._now(),
        )
        if account is None:
            raise AuthError(AuthErrorCode.USER_NOT_FOUND)
        return account.managed_view()


def _require_admin(user: CurrentUser) -> None:
    if user.role is not UserRole.ADMIN:
        raise AuthError(AuthErrorCode.FORBIDDEN)
