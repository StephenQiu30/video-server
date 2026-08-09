from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.application.auth import CurrentUser


class EmailPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=320, examples=["user@example.com"])
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime

    @classmethod
    def from_user(cls, user: CurrentUser) -> UserResponse:
        return cls(id=user.id, email=user.email, created_at=user.created_at)
