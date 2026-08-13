from __future__ import annotations

from datetime import datetime

from pydantic import Field, SecretStr, model_validator

from app.api.schemas.common import StrictModel
from app.application.ai_providers import (
    AiProviderAuthMode,
    AiProviderEngine,
    AiProviderProfile,
)


class AiProviderProfileResponse(StrictModel):
    key: str
    display_name: str
    engine: AiProviderEngine
    auth_mode: AiProviderAuthMode
    base_url: str | None
    model: str
    credential_configured: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, value: AiProviderProfile) -> AiProviderProfileResponse:
        return cls(
            key=value.key,
            display_name=value.display_name,
            engine=value.engine,
            auth_mode=value.auth_mode,
            base_url=value.base_url,
            model=value.model,
            credential_configured=value.credential_configured,
            is_active=value.is_active,
            created_at=value.created_at,
            updated_at=value.updated_at,
        )


class AiProviderProfileListResponse(StrictModel):
    items: tuple[AiProviderProfileResponse, ...]
    agent_available: bool


class CreateAiProviderProfileRequest(StrictModel):
    key: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=64)
    engine: AiProviderEngine
    auth_mode: AiProviderAuthMode
    base_url: str | None = Field(default=None, max_length=2048)
    model: str = Field(min_length=1, max_length=128)
    api_key: SecretStr | None = Field(default=None, max_length=4096)

    def service_values(self) -> dict[str, object]:
        return {
            **self.model_dump(exclude={"api_key"}),
            "api_key": self.api_key.get_secret_value() if self.api_key else None,
        }


class UpdateAiProviderProfileRequest(StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    engine: AiProviderEngine | None = None
    auth_mode: AiProviderAuthMode | None = None
    base_url: str | None = Field(default=None, max_length=2048)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    api_key: SecretStr | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def require_change(self) -> UpdateAiProviderProfileRequest:
        if not self.model_fields_set:
            raise ValueError("at least one change is required")
        return self

    def service_values(self) -> dict[str, object]:
        return {
            "display_name": self.display_name,
            "engine": self.engine,
            "auth_mode": self.auth_mode,
            "base_url": self.base_url,
            "base_url_changed": "base_url" in self.model_fields_set,
            "model": self.model,
            "api_key": self.api_key.get_secret_value() if self.api_key else None,
        }
