from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.services.quotas import UserQuota


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


@dataclass(frozen=True, slots=True)
class AccountRecord:
    id: UUID
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    quota: UserQuota = UserQuota()
    avatar_version: UUID | None = None

    def public_view(self) -> CurrentUser:
        return CurrentUser(
            id=self.id,
            username=self.username,
            email=self.email,
            role=self.role,
            created_at=self.created_at,
            updated_at=self.updated_at,
            quota=self.quota,
            avatar_version=self.avatar_version,
        )

    def managed_view(self) -> ManagedUser:
        return ManagedUser(
            id=self.id,
            username=self.username,
            email=self.email,
            role=self.role,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            quota=self.quota,
        )


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    username: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    quota: UserQuota = UserQuota()
    avatar_version: UUID | None = None

    @property
    def owner_hash(self) -> str:
        return hashlib.sha256(str(self.id).encode()).hexdigest()

    @property
    def is_admin(self) -> bool:
        return self.role is UserRole.ADMIN

    @property
    def admission_quota(self) -> UserQuota:
        if self.is_admin:
            return UserQuota(exempt=True)
        return self.quota


@dataclass(frozen=True, slots=True)
class ManagedUser:
    id: UUID
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    quota: UserQuota = UserQuota()


@dataclass(frozen=True, slots=True)
class ManagedUserPage:
    items: tuple[ManagedUser, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class PasswordCheck:
    valid: bool
    updated_hash: str | None = None


@dataclass(frozen=True, slots=True)
class SessionGrant:
    user: CurrentUser
    access_token: str
    refresh_token: str
    access_expires_at: datetime
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
    access_expires_at: datetime
    refresh_expires_at: datetime
