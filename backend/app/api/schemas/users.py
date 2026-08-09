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

from app.application.auth import ManagedUser, ManagedUserPage, UserRole
from app.application.auth.usernames import normalize_username


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

    @model_validator(mode="after")
    def require_change(self) -> UpdateUserAccessRequest:
        if self.role is None and self.is_active is None:
            raise ValueError("role or is_active is required")
        return self
