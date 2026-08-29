"""Models and ports for administrator-managed AI analysis Providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

LOCAL_CODEX_PROVIDER_KEY = "local-codex"


class AiProviderEngine(StrEnum):
    CODEX = "codex"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"


class AiProviderAuthMode(StrEnum):
    HOST_LOGIN = "host_login"
    API_KEY = "api_key"


@dataclass(frozen=True, slots=True)
class AiProviderProfile:
    key: str
    display_name: str
    engine: AiProviderEngine
    auth_mode: AiProviderAuthMode
    base_url: str | None
    model: str
    credential_ciphertext: bytes | None
    credential_key_id: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @property
    def credential_configured(self) -> bool:
        return self.credential_ciphertext is not None


class AiProviderErrorCode(StrEnum):
    FORBIDDEN = "forbidden"
    INVALID_PROFILE = "invalid_ai_provider_profile"
    CONFLICT = "ai_provider_conflict"
    NOT_FOUND = "ai_provider_not_found"
    ACTIVE_DELETE = "active_ai_provider_delete"
    RESERVED_MUTATION = "reserved_ai_provider_mutation"


class AiProviderError(RuntimeError):
    def __init__(self, code: AiProviderErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class DuplicateAiProviderKeyError(RuntimeError):
    pass


class AiProviderSecretCipher(Protocol):
    @property
    def key_id(self) -> str: ...

    def encrypt(self, provider_key: str, secret: str) -> bytes: ...


class AnalysisAgentAvailability(Protocol):
    async def is_available(self, now: datetime) -> bool: ...


class AiProviderRepository(Protocol):
    async def list_profiles(self) -> tuple[AiProviderProfile, ...]: ...

    async def get_profile(self, key: str) -> AiProviderProfile | None: ...

    async def get_active_profile(self) -> AiProviderProfile | None: ...

    async def create_profile(
        self,
        *,
        key: str,
        display_name: str,
        engine: AiProviderEngine,
        auth_mode: AiProviderAuthMode,
        base_url: str | None,
        model: str,
        credential_ciphertext: bytes | None,
        credential_key_id: str | None,
        now: datetime,
    ) -> AiProviderProfile: ...

    async def update_profile(
        self,
        key: str,
        *,
        display_name: str | None,
        engine: AiProviderEngine | None,
        auth_mode: AiProviderAuthMode | None,
        base_url: str | None,
        base_url_changed: bool,
        model: str | None,
        credential_ciphertext: bytes | None,
        credential_key_id: str | None,
        credential_changed: bool,
        now: datetime,
    ) -> AiProviderProfile | None: ...

    async def activate_profile(
        self, key: str, *, now: datetime
    ) -> AiProviderProfile | None: ...

    async def delete_profile(self, key: str) -> bool: ...
