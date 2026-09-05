from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.api.auth_dependencies import get_current_admin, get_current_user
from app.application.auth import CurrentUser, UserRole
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from tests.integration.api.fakes import use_cases

ADMIN = CurrentUser(
    id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    username="admin_user",
    email="admin@example.com",
    role=UserRole.ADMIN,
    created_at=datetime(2026, 8, 1, tzinfo=UTC),
    updated_at=datetime(2026, 8, 1, tzinfo=UTC),
)
USER = CurrentUser(
    id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    username="normal_user",
    email="user@example.com",
    role=UserRole.USER,
    created_at=datetime(2026, 8, 1, tzinfo=UTC),
    updated_at=datetime(2026, 8, 1, tzinfo=UTC),
)


def test_admin_download_analytics_returns_visualization_safe_fields(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(app_env="test"))
    container, stubs = use_cases()
    app.state.download_use_cases = container
    app.dependency_overrides[get_current_admin] = lambda: ADMIN

    with TestClient(app) as client:
        response = client.get("/api/admin/downloads/analytics", params={"days": 7})

    assert response.status_code == 200
    payload = response.json()
    assert payload["period_days"] == 7
    assert payload["summary"] == {
        "total": 4,
        "succeeded": 3,
        "failed": 1,
        "cancelled": 0,
        "active": 0,
        "unique_users": 2,
        "downloaded_bytes": 12_345,
        "average_duration_seconds": 90.5,
        "success_rate": 75.0,
    }
    assert payload["daily"][0]["date"] == "2026-08-06"
    assert payload["sources"][0]["source_name"] == "YouTube"
    assert stubs["analytics"].calls == [((ADMIN,), {"days": 7})]
    assert all(
        sensitive not in response.text
        for sensitive in ("owner_hash", "url", "provider_hints", "error_message")
    )


def test_admin_download_analytics_rejects_non_admin(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test"))
    container, stubs = use_cases()
    app.state.download_use_cases = container
    app.dependency_overrides[get_current_user] = lambda: USER

    with TestClient(app) as client:
        response = client.get("/api/admin/downloads/analytics")

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert stubs["analytics"].calls == []
