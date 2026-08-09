from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.application.auth import CurrentUser, UserRole
from app.application.auth.usernames import normalize_username


class EmailPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320, examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(EmailPasswordRequest):
    username: str = Field(
        min_length=2,
        max_length=32,
        examples=["video_user"],
        description="唯一用户名，支持字母、数字、中文以及 _-. 字符。",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        display, _normalized = normalize_username(value)
        return display


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: CurrentUser) -> UserResponse:
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
