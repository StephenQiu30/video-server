from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.services.auth.models import CurrentUser, UserRole
from app.services.auth.usernames import normalize_username


class EmailPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320, examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128)


class RegistrationCodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=320)


class RegistrationCodeResponse(BaseModel):
    email_sent: bool = True
    expires_in_seconds: int = 600
    retry_after_seconds: int = 60


class RegistrationCodeVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320)
    verification_code: str = Field(pattern=r"^[0-9]{6}$", min_length=6, max_length=6)


class RegistrationCodeVerificationResponse(BaseModel):
    verified: bool = True


class RegisterRequest(EmailPasswordRequest):
    verification_code: str = Field(pattern=r"^[0-9]{6}$", min_length=6, max_length=6)
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
    avatar_version: UUID | None = None

    @classmethod
    def from_user(cls, user: CurrentUser) -> UserResponse:
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
            avatar_version=user.avatar_version,
        )
