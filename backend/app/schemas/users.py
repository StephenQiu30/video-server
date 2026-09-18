from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.services.auth.models import ManagedUser, ManagedUserPage, UserRole
from app.services.auth.usernames import normalize_username
from app.services.quotas import UserQuota


class UserQuotaSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exempt: bool = False
    max_active_per_owner: int | None = Field(default=None, ge=1)
    daily_tasks: int | None = Field(default=None, ge=1)
    daily_bytes: int | None = Field(default=None, ge=1)
    storage_bytes: int | None = Field(default=None, ge=1)
    daily_analysis_attempts: int | None = Field(default=None, ge=1)

    @classmethod
    def from_quota(cls, quota: UserQuota) -> UserQuotaSettings:
        return cls(
            exempt=quota.exempt,
            max_active_per_owner=quota.max_active_per_owner,
            daily_tasks=quota.daily_tasks,
            daily_bytes=quota.daily_bytes,
            storage_bytes=quota.storage_bytes,
            daily_analysis_attempts=quota.daily_analysis_attempts,
        )

    def to_quota(self) -> UserQuota:
        return UserQuota(**self.model_dump())


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=2, max_length=32)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        display, _normalized = normalize_username(value)
        return display


class ManagedUserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    quota: UserQuotaSettings

    @classmethod
    def from_user(cls, user: ManagedUser) -> ManagedUserResponse:
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            quota=UserQuotaSettings.from_quota(user.quota),
        )


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    page: int
    page_size: int
    total: int

    @classmethod
    def from_page(cls, page: ManagedUserPage) -> ManagedUserListResponse:
        return cls(
            items=[ManagedUserResponse.from_user(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total=page.total,
        )


class UpdateUserAccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    is_active: bool | None = None
    quota: UserQuotaSettings | None = None

    @model_validator(mode="after")
    def require_change(self) -> UpdateUserAccessRequest:
        if self.role is None and self.is_active is None and self.quota is None:
            raise ValueError("role, is_active or quota is required")
        return self
