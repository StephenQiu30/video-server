from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.api.auth_dependencies import get_current_admin, get_current_user
from app.application.ai_providers import (
    AiProviderProfile,
)
from app.application.auth import CurrentUser, UserRole
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 13, tzinfo=UTC)
ADMIN = CurrentUser(
    UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    "admin",
    "admin@example.com",
    UserRole.ADMIN,
    NOW,
    NOW,
)
USER = replace(ADMIN, role=UserRole.USER)


class Providers:
    def __init__(self) -> None:
        self.items: dict[str, AiProviderProfile] = {}
        self.received_secret: str | None = None

    async def list_profiles(self, actor: CurrentUser):
        assert actor == ADMIN
        return tuple(self.items.values())

    async def agent_available(self, actor: CurrentUser) -> bool:
        assert actor == ADMIN
        return True

    async def create_profile(self, actor: CurrentUser, **values: object):
        assert actor == ADMIN
        self.received_secret = str(values.pop("api_key"))
        profile = AiProviderProfile(
            **values,  # type: ignore[arg-type]
            credential_ciphertext=b"ciphertext",
            credential_key_id="fernet-test",
            is_active=False,
            created_at=NOW,
            updated_at=NOW,
        )
        self.items[profile.key] = profile
        return profile

    async def update_profile(self, actor: CurrentUser, key: str, **values: object):
        assert actor == ADMIN
        self.received_secret = (
            str(values["api_key"]) if values["api_key"] is not None else None
        )
        current = self.items[key]
        result = replace(current, display_name=str(values["display_name"]))
        self.items[key] = result
        return result

    async def activate_profile(self, actor: CurrentUser, key: str):
        assert actor == ADMIN
        self.items = {
            item_key: replace(item, is_active=item_key == key)
            for item_key, item in self.items.items()
        }
        return self.items[key]

    async def delete_profile(self, actor: CurrentUser, key: str) -> None:
        assert actor == ADMIN
        self.items.pop(key)


def test_admin_crud_never_returns_ai_provider_secret(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    providers = Providers()
    app.state.ai_provider_service = providers
    app.dependency_overrides[get_current_admin] = lambda: ADMIN

    with TestClient(app) as client:
        created = client.post(
            "/api/admin/ai-providers",
            json={
                "key": "openai-main",
                "display_name": "OpenAI Main",
                "engine": "codex",
                "auth_mode": "api_key",
                "base_url": "https://api.example.com/v1",
                "model": "gpt-custom",
                "api_key": "secret-value",
            },
        )
        listed = client.get("/api/admin/ai-providers")
        updated = client.patch(
            "/api/admin/ai-providers/openai-main",
            json={"display_name": "OpenAI Rotated", "api_key": "rotated-secret"},
        )
        activated = client.post("/api/admin/ai-providers/openai-main/activate")

    assert created.status_code == 201
    assert created.headers["location"] == "/api/admin/ai-providers/openai-main"
    assert providers.received_secret == "rotated-secret"
    assert "api_key" not in created.json()
    assert "ciphertext" not in created.text
    assert updated.status_code == 200
    assert "rotated-secret" not in updated.text
    assert "api_key" not in updated.json()
    assert listed.json()["agent_available"] is True
    assert activated.json()["is_active"] is True


def test_ai_provider_routes_reject_non_admin(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    providers = Providers()
    app.state.ai_provider_service = providers
    app.dependency_overrides[get_current_user] = lambda: USER

    with TestClient(app) as client:
        response = client.get("/api/admin/ai-providers")

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
