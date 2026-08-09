from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from .errors import AuthError, AuthErrorCode, DuplicateEmailError
from .models import CurrentUser, SessionGrant
from .ports import AuthRepository, AuthTokens, PasswordHasher


class AuthService:
    def __init__(
        self,
        *,
        repository: AuthRepository,
        passwords: PasswordHasher,
        tokens: AuthTokens,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
    ) -> None:
        self._repository = repository
        self._passwords = passwords
        self._tokens = tokens
        self._now = now
        self._new_id = new_id

    async def register(self, email: str, password: str) -> SessionGrant:
        normalized = _normalize_email(email)
        _validate_password(password)
        password_hash = await self._passwords.hash(password)
        now = self._now()
        try:
            account = await self._repository.create_account(
                account_id=self._new_id(),
                email=normalized,
                password_hash=password_hash,
                now=now,
            )
        except DuplicateEmailError as exc:
            raise AuthError(AuthErrorCode.EMAIL_ALREADY_REGISTERED) from exc
        return await self._grant(account.public_view(), now)

    async def login(self, email: str, password: str) -> SessionGrant:
        account = await self._repository.find_account_by_email(_normalize_email(email))
        checked = await self._passwords.verify(
            password, account.password_hash if account is not None else None
        )
        if account is None or not account.is_active or not checked.valid:
            raise AuthError(AuthErrorCode.INVALID_CREDENTIALS)
        now = self._now()
        if checked.updated_hash is not None:
            await self._repository.update_password_hash(
                account.id, checked.updated_hash, now
            )
        return await self._grant(account.public_view(), now)

    async def current_user(self, access_token: str) -> CurrentUser:
        claims = self._tokens.decode_access(access_token)
        account = (
            await self._repository.find_account_by_id(claims.user_id)
            if claims is not None
            else None
        )
        if account is None or not account.is_active:
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        return account.public_view()

    async def refresh(self, refresh_token: str) -> SessionGrant:
        claims = self._tokens.decode_refresh(refresh_token)
        previous_hash = self._tokens.digest(refresh_token)
        now = self._now()
        user = (
            await self._repository.find_user_by_session(previous_hash, now)
            if claims is not None and previous_hash
            else None
        )
        if user is None or claims is None or user.id != claims.user_id:
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        return await self._grant(user, now, previous_token_hash=previous_hash)

    async def logout(self, refresh_token: str) -> None:
        token_hash = self._tokens.digest(refresh_token)
        if token_hash:
            await self._repository.delete_session(token_hash)

    async def _grant(
        self,
        user: CurrentUser,
        now: datetime,
        *,
        previous_token_hash: str | None = None,
    ) -> SessionGrant:
        issued = self._tokens.issue(user.id, now)
        if previous_token_hash is None:
            await self._repository.create_session(
                session_id=self._new_id(),
                user_id=user.id,
                token_hash=issued.refresh_token_hash,
                expires_at=issued.refresh_expires_at,
                now=now,
            )
        else:
            replaced = await self._repository.replace_session(
                previous_token_hash=previous_token_hash,
                session_id=self._new_id(),
                user_id=user.id,
                token_hash=issued.refresh_token_hash,
                expires_at=issued.refresh_expires_at,
                now=now,
            )
            if not replaced:
                raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        return SessionGrant(
            user,
            issued.access_token,
            issued.refresh_token,
            issued.refresh_expires_at,
        )


def _normalize_email(email: str) -> str:
    return email.strip().casefold()


def _validate_password(password: str) -> None:
    if not 8 <= len(password) <= 128:
        raise ValueError("password must contain between 8 and 128 characters")
