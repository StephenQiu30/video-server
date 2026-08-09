from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from .models import AccountRecord, CurrentUser, IssuedTokens, PasswordCheck, TokenClaims


class AuthRepository(Protocol):
    async def create_account(
        self,
        *,
        account_id: UUID,
        email: str,
        password_hash: str,
        now: datetime,
    ) -> AccountRecord: ...

    async def find_account_by_email(self, email: str) -> AccountRecord | None: ...

    async def find_account_by_id(self, account_id: UUID) -> AccountRecord | None: ...

    async def update_password_hash(
        self, account_id: UUID, password_hash: str, now: datetime
    ) -> None: ...

    async def create_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None: ...

    async def find_user_by_session(
        self, token_hash: str, now: datetime
    ) -> CurrentUser | None: ...

    async def delete_session(self, token_hash: str) -> None: ...

    async def replace_session(
        self,
        *,
        previous_token_hash: str,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> bool: ...


class PasswordHasher(Protocol):
    async def hash(self, password: str) -> str: ...

    async def verify(
        self, password: str, password_hash: str | None
    ) -> PasswordCheck: ...


class AuthTokens(Protocol):
    def issue(self, user_id: UUID, now: datetime) -> IssuedTokens: ...

    def decode_access(self, token: str) -> TokenClaims | None: ...

    def decode_refresh(self, token: str) -> TokenClaims | None: ...

    def digest(self, token: str) -> str: ...
