"""One stable opaque Web cookie; native Bearer sessions have a separate owner."""

import asyncio
import hashlib
import re
import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.core.errors import AppError
from app.services.auth.errors import AuthError, AuthErrorCode, SessionStoreUnavailable
from app.services.auth.models import CurrentUser

_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


class WebSessionPersistence(Protocol):
    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        previous_hash: str | None,
        now: datetime,
        idle_expires_at: datetime,
        absolute_expires_at: datetime,
    ) -> CurrentUser | None: ...
    async def current_user(
        self, token_hash: str, *, now: datetime, idle_ttl: timedelta, touch: bool
    ) -> CurrentUser | None: ...
    async def revoke(self, token_hash: str, *, now: datetime) -> UUID | None: ...


@dataclass(frozen=True, slots=True)
class WebSessionGrant:
    user: CurrentUser
    token: str = field(repr=False)
    expires_at: datetime


class WebSessionService:
    def __init__(
        self,
        repository: WebSessionPersistence,
        *,
        now: Callable[[], datetime],
        idle_ttl: timedelta,
        absolute_ttl: timedelta,
    ) -> None:
        if not timedelta(minutes=1) <= idle_ttl <= absolute_ttl:
            raise ValueError("invalid Web session lifetime")
        self._repository = repository
        self._now = now
        self._idle_ttl = idle_ttl
        self._absolute_ttl = absolute_ttl

    async def issue(
        self, user_id: UUID, *, previous_token: str | None = None
    ) -> WebSessionGrant:
        now = self._now()
        token = secrets.token_urlsafe(32)
        expires_at = now + self._absolute_ttl
        async with _database_operation():
            user = await self._repository.create(
                user_id=user_id,
                token_hash=_digest(token) or "",
                previous_hash=_digest(previous_token),
                now=now,
                idle_expires_at=now + self._idle_ttl,
                absolute_expires_at=expires_at,
            )
        if user is None:
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        return WebSessionGrant(user, token, expires_at)

    async def current_user(self, token: str, *, touch: bool = True) -> CurrentUser:
        digest = _digest(token)
        if digest is None:
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        async with _database_operation():
            user = await self._repository.current_user(
                digest, now=self._now(), idle_ttl=self._idle_ttl, touch=touch
            )
        if user is None:
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)
        return user

    async def revoke(self, token: str) -> UUID | None:
        digest = _digest(token)
        if digest is None:
            return None
        async with _database_operation():
            return await self._repository.revoke(digest, now=self._now())


def _digest(token: str | None) -> str | None:
    return (
        hashlib.sha256(token.encode()).hexdigest()
        if token and _TOKEN.fullmatch(token)
        else None
    )


@asynccontextmanager
async def _database_operation() -> AsyncIterator[None]:
    try:
        async with asyncio.timeout(5):
            yield
    except (SessionStoreUnavailable, OSError, TimeoutError) as exc:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Session service unavailable",
            detail="登录状态暂时无法确认，请稍后重试。",
        ) from exc
