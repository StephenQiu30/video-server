from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.auth import UserResponse
from app.application.auth import SessionGrant


class NativeRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1, max_length=4096)


class NativeLogoutRequest(NativeRefreshRequest):
    pass


class NativeSessionResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"]
    access_expires_at: datetime
    refresh_expires_at: datetime

    @classmethod
    def from_grant(cls, grant: SessionGrant) -> NativeSessionResponse:
        return cls(
            user=UserResponse.from_user(grant.user),
            access_token=grant.access_token,
            refresh_token=grant.refresh_token,
            token_type="Bearer",
            access_expires_at=grant.access_expires_at,
            refresh_expires_at=grant.refresh_expires_at,
        )
