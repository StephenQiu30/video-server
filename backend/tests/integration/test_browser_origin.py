from unittest.mock import AsyncMock

import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "null",
        "http://testserver:8000",
        "http://testserver:0",
        "https://testserver",
        "http://testserver.evil",
        "http://evil@ localhost",
        "http://testserver,http://evil",
    ],
)
def test_rejects_missing_opaque_or_different_origins_before_login(origin):
    app = create_app(Settings(app_env="test"))
    auth = AsyncMock()
    app.state.services.auth_service = auth
    headers = {} if origin is None else {"Origin": origin}
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            headers=headers,
            json={"email": "user@example.com", "password": "strong-password"},
        )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert "set-cookie" not in response.headers
    auth.authenticate.assert_not_awaited()


def test_cookie_mutations_require_origin_but_explicit_bearer_does_not_fall_back():
    app = create_app(Settings(app_env="test"))
    with TestClient(app) as client:
        client.cookies.set("video_web_session", "a" * 43)
        assert (
            client.patch("/api/users/me", json={"username": "safe_user"}).status_code
            == 403
        )
        response = client.patch(
            "/api/users/me",
            headers={"Authorization": "Basic invalid"},
            json={"username": "safe_user"},
        )
        assert response.status_code != 403  # Auth rejects/503; never consumes cookie.
        response = client.post(
            "/api/auth/logout", headers={"Referer": "http://testserver/history"}
        )
        assert response.status_code == 503  # Origin passed; session service absent.
