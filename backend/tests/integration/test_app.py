from __future__ import annotations

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


class StubReadinessProbe:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def check(self) -> bool:
        return self.ready


def test_health_and_ready_contract() -> None:
    app = create_app(Settings(app_env="test"))

    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.json() == {"status": "ok"}
    assert ready.json() == {"status": "ok", "service": "api"}


def test_ready_returns_503_when_a_runtime_dependency_is_unavailable() -> None:
    app = create_app(Settings(app_env="test"))
    app.state.readiness_probe = StubReadinessProbe(False)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "service": "api"}


def test_backend_does_not_serve_frontend_pages() -> None:
    app = create_app(Settings(app_env="test"))

    with TestClient(app) as client:
        index = client.get("/")
        route = client.get("/missing-page")
        asset = client.get("/_next/static/chunks/app.js")

    for response in (index, route, asset):
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")


def test_unknown_api_never_falls_back_to_frontend() -> None:
    app = create_app(Settings(app_env="test"))

    with TestClient(app) as client:
        response = client.get("/api/not-found")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
