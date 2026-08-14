from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.application.ai_providers import (
    AiProviderAuthMode,
    AiProviderEngine,
    AiProviderError,
    AiProviderErrorCode,
    AiProviderProfile,
    AiProviderService,
    DuplicateAiProviderKeyError,
)
from app.application.auth import CurrentUser, UserRole

NOW = datetime(2026, 8, 13, tzinfo=UTC)
ADMIN = CurrentUser(
    UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    "admin",
    "admin@example.com",
    UserRole.ADMIN,
    NOW,
    NOW,
)
USER = replace(
    ADMIN,
    id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    role=UserRole.USER,
)


class Cipher:
    key_id = "fernet-test"

    def encrypt(self, provider_key: str, secret: str) -> bytes:
        return f"{provider_key}:{secret}".encode()


class Availability:
    async def is_available(self, now: datetime) -> bool:
        assert now == NOW
        return True


class Repository:
    def __init__(self) -> None:
        self.items: dict[str, AiProviderProfile] = {}

    async def list_profiles(self) -> tuple[AiProviderProfile, ...]:
        return tuple(self.items.values())

    async def get_profile(self, key: str) -> AiProviderProfile | None:
        return self.items.get(key)

    async def get_active_profile(self) -> AiProviderProfile | None:
        return next((item for item in self.items.values() if item.is_active), None)

    async def create_profile(self, **values: object) -> AiProviderProfile:
        key = str(values["key"])
        if key in self.items:
            raise DuplicateAiProviderKeyError
        now = values["now"]
        profile = AiProviderProfile(
            key=key,
            display_name=str(values["display_name"]),
            engine=values["engine"],  # type: ignore[arg-type]
            auth_mode=values["auth_mode"],  # type: ignore[arg-type]
            base_url=values["base_url"],  # type: ignore[arg-type]
            model=str(values["model"]),
            credential_ciphertext=values["credential_ciphertext"],  # type: ignore[arg-type]
            credential_key_id=values["credential_key_id"],  # type: ignore[arg-type]
            is_active=False,
            created_at=now,  # type: ignore[arg-type]
            updated_at=now,  # type: ignore[arg-type]
        )
        self.items[key] = profile
        return profile

    async def update_profile(
        self, key: str, **values: object
    ) -> AiProviderProfile | None:
        current = self.items.get(key)
        if current is None:
            return None
        changes: dict[str, object] = {"updated_at": values["now"]}
        for field in ("display_name", "engine", "auth_mode", "model"):
            if values[field] is not None:
                changes[field] = values[field]
        if values["base_url_changed"]:
            changes["base_url"] = values["base_url"]
        if values["credential_changed"]:
            changes["credential_ciphertext"] = values["credential_ciphertext"]
            changes["credential_key_id"] = values["credential_key_id"]
        result = replace(current, **changes)
        self.items[key] = result
        return result

    async def activate_profile(
        self, key: str, *, now: datetime
    ) -> AiProviderProfile | None:
        if key not in self.items:
            return None
        self.items = {
            item_key: replace(item, is_active=item_key == key, updated_at=now)
            for item_key, item in self.items.items()
        }
        return self.items[key]

    async def delete_profile(self, key: str) -> bool:
        return self.items.pop(key, None) is not None


def service(repository: Repository) -> AiProviderService:
    return AiProviderService(
        repository, Cipher(), now=lambda: NOW, availability=Availability()
    )


@pytest.mark.asyncio
async def test_api_key_profile_is_encrypted_and_activated() -> None:
    repository = Repository()
    providers = service(repository)

    created = await providers.create_profile(
        ADMIN,
        key="openai-main",
        display_name=" OpenAI  Main ",
        engine=AiProviderEngine.CODEX,
        auth_mode=AiProviderAuthMode.API_KEY,
        base_url="https://api.example.com/v1/",
        model="gpt-custom",
        api_key="secret-value",
    )
    active = await providers.activate_profile(ADMIN, created.key)

    assert created.display_name == "OpenAI Main"
    assert created.base_url == "https://api.example.com/v1"
    assert created.credential_ciphertext == b"openai-main:secret-value"
    assert created.credential_configured is True
    assert active.is_active is True
    assert await providers.agent_available(ADMIN) is True


@pytest.mark.asyncio
async def test_switching_to_host_login_clears_endpoint_and_encrypted_key() -> None:
    repository = Repository()
    providers = service(repository)
    created = await providers.create_profile(
        ADMIN,
        key="custom",
        display_name="Custom",
        engine=AiProviderEngine.CLAUDE,
        auth_mode=AiProviderAuthMode.API_KEY,
        base_url="https://api.example.com",
        model="sonnet",
        api_key="secret-value",
    )

    updated = await providers.update_profile(
        ADMIN,
        created.key,
        display_name=None,
        engine=None,
        auth_mode=AiProviderAuthMode.HOST_LOGIN,
        base_url=None,
        base_url_changed=False,
        model=None,
        api_key=None,
    )

    assert updated.auth_mode is AiProviderAuthMode.HOST_LOGIN
    assert updated.base_url is None
    assert updated.credential_configured is False


@pytest.mark.asyncio
async def test_api_key_update_preserves_blank_and_rotates_new_secret() -> None:
    repository = Repository()
    providers = service(repository)
    created = await providers.create_profile(
        ADMIN,
        key="custom",
        display_name="Custom",
        engine=AiProviderEngine.CODEX,
        auth_mode=AiProviderAuthMode.API_KEY,
        base_url="https://api.example.com/v1",
        model="gpt-custom",
        api_key="first-secret",
    )

    preserved = await providers.update_profile(
        ADMIN,
        created.key,
        display_name="Renamed",
        engine=None,
        auth_mode=None,
        base_url=None,
        base_url_changed=False,
        model=None,
        api_key=None,
    )
    rotated = await providers.update_profile(
        ADMIN,
        created.key,
        display_name=None,
        engine=None,
        auth_mode=None,
        base_url=None,
        base_url_changed=False,
        model=None,
        api_key="second-secret",
    )

    assert preserved.display_name == "Renamed"
    assert preserved.credential_ciphertext == b"custom:first-secret"
    assert rotated.credential_ciphertext == b"custom:second-secret"
    assert rotated.credential_key_id == Cipher.key_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "base_url",
    (
        "http://api.example.com/v1",
        "https://user:pass@api.example.com/v1",
        "https://api.example.com/v1?token=secret",
    ),
)
async def test_rejects_unsafe_public_endpoints(base_url: str) -> None:
    with pytest.raises(AiProviderError) as error:
        await service(Repository()).create_profile(
            ADMIN,
            key="unsafe",
            display_name="Unsafe",
            engine=AiProviderEngine.CODEX,
            auth_mode=AiProviderAuthMode.API_KEY,
            base_url=base_url,
            model="model",
            api_key="secret",
        )
    assert error.value.code is AiProviderErrorCode.INVALID_PROFILE


@pytest.mark.asyncio
async def test_forbids_non_admin_and_active_delete() -> None:
    repository = Repository()
    providers = service(repository)
    with pytest.raises(AiProviderError) as forbidden:
        await providers.list_profiles(USER)
    assert forbidden.value.code is AiProviderErrorCode.FORBIDDEN

    created = await providers.create_profile(
        ADMIN,
        key="local-codex",
        display_name="Local Codex",
        engine=AiProviderEngine.CODEX,
        auth_mode=AiProviderAuthMode.HOST_LOGIN,
        base_url=None,
        model="gpt-test",
        api_key=None,
    )
    await providers.activate_profile(ADMIN, created.key)
    with pytest.raises(AiProviderError) as active_delete:
        await providers.delete_profile(ADMIN, created.key)
    assert active_delete.value.code is AiProviderErrorCode.ACTIVE_DELETE
