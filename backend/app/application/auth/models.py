from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccountRecord:
    id: UUID
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime

    def public_view(self) -> CurrentUser:
        return CurrentUser(id=self.id, email=self.email, created_at=self.created_at)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    email: str
    created_at: datetime

    @property
    def owner_hash(self) -> str:
        return hashlib.sha256(str(self.id).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PasswordCheck:
    valid: bool
    updated_hash: str | None = None


@dataclass(frozen=True, slots=True)
class SessionGrant:
    user: CurrentUser
    access_token: str
    refresh_token: str
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: UUID
    token_id: UUID
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    refresh_token_hash: str
    refresh_expires_at: datetime
