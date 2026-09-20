"""Registration email proof; independent of browser/native sessions."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.services.auth.errors import AuthError, AuthErrorCode


class VerificationStore(Protocol):
    async def reserve(
        self,
        email: str,
        generation: UUID,
        digest: str,
        now: datetime,
        expires_at: datetime,
    ) -> bool: ...
    async def mark_sent(self, email: str, generation: UUID) -> bool: ...
    async def invalidate(self, email: str, generation: UUID) -> None: ...
    async def verify(self, email: str, digest: str, now: datetime) -> bool: ...
    async def consume(self, email: str, digest: str, now: datetime) -> bool: ...


class RegistrationMailer(Protocol):
    async def send_code(self, email: str, code: str) -> None: ...


class EmailVerification:
    def __init__(
        self,
        store: VerificationStore,
        mailer: RegistrationMailer,
        secret: bytes,
        now: Callable[[], datetime],
    ) -> None:
        self._store = store
        self._mailer = mailer
        self._secret = secret
        self._now = now

    def _digest(self, email: str, code: str) -> str:
        return hmac.new(
            self._secret, f"registration:{email}:{code}".encode(), hashlib.sha256
        ).hexdigest()

    async def send(self, email: str) -> None:
        email = email.strip().casefold()
        code = f"{secrets.randbelow(1_000_000):06d}"
        generation = uuid4()
        now = self._now()
        if not await self._store.reserve(
            email,
            generation,
            self._digest(email, code),
            now,
            now + timedelta(minutes=10),
        ):
            raise AuthError(AuthErrorCode.VERIFICATION_RATE_LIMITED)
        try:
            await self._mailer.send_code(email, code)
            if not await self._store.mark_sent(email, generation):
                raise AuthError(AuthErrorCode.EMAIL_SEND_FAILED)
        except BaseException:
            await asyncio.shield(self._store.invalidate(email, generation))
            raise

    async def consume(self, email: str, code: str) -> None:
        email = email.strip().casefold()
        if not await self._store.consume(email, self._digest(email, code), self._now()):
            raise AuthError(AuthErrorCode.INVALID_VERIFICATION_CODE)

    async def verify(self, email: str, code: str) -> None:
        email = email.strip().casefold()
        if not await self._store.verify(email, self._digest(email, code), self._now()):
            raise AuthError(AuthErrorCode.INVALID_VERIFICATION_CODE)
