from __future__ import annotations

from pathlib import Path
from typing import Annotated

from app.api.dependencies import get_anonymous_session
from app.core.config import Settings
from app.core.session import AnonymousSession
from app.main import create_app
from fastapi import Depends
from fastapi.testclient import TestClient


def build_session_app(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            app_env="test",
            session_cookie_name="test_session",
            frontend_dist_dir=tmp_path / "missing",
        )
    )

    @app.get("/api/session")
    async def session_route(
        session: Annotated[AnonymousSession, Depends(get_anonymous_session)],
    ) -> dict[str, str]:
        return {"owner_hash": session.owner_hash}

    return TestClient(app)


def test_anonymous_session_is_http_only_and_stable(tmp_path: Path) -> None:
    with build_session_app(tmp_path) as client:
        first = client.get("/api/session")
        second = client.get("/api/session")

    assert first.json() == second.json()
    cookie = first.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_tampered_cookie_is_replaced(tmp_path: Path) -> None:
    with build_session_app(tmp_path) as client:
        first = client.get("/api/session")
        client.cookies.set("test_session", "tampered")
        second = client.get("/api/session")

    assert first.json() != second.json()
    assert "set-cookie" in second.headers
