from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


class StubReadinessProbe:
    def __init__(self, ready: bool) -> None:
        self.ready = ready

    async def check(self) -> bool:
        return self.ready


def build_dist(root: Path) -> Path:
    dist = root / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><title>server-ui</title><div id='root'></div>",
        encoding="utf-8",
    )
    (assets / "app.js").write_text("window.SERVER_UI = true;", encoding="utf-8")
    return dist


def test_health_and_ready_contract(tmp_path: Path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "missing"))

    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.json() == {"status": "ok"}
    assert ready.json() == {"status": "ok", "service": "api"}


def test_ready_returns_503_when_a_runtime_dependency_is_unavailable(
    tmp_path: Path,
) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "missing"))
    app.state.readiness_probe = StubReadinessProbe(False)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "service": "api"}


def test_frontend_is_same_origin_and_supports_spa_routes(tmp_path: Path) -> None:
    dist = build_dist(tmp_path)
    app = create_app(Settings(app_env="test", frontend_dist_dir=dist))

    with TestClient(app) as client:
        index = client.get("/")
        deep_link = client.get("/downloads/123")
        asset = client.get("/assets/app.js")

    assert index.status_code == 200
    assert "server-ui" in index.text
    assert deep_link.status_code == 200
    assert "server-ui" in deep_link.text
    assert asset.text == "window.SERVER_UI = true;"


def test_unknown_api_never_falls_back_to_frontend(tmp_path: Path) -> None:
    dist = build_dist(tmp_path)
    app = create_app(Settings(app_env="test", frontend_dist_dir=dist))

    with TestClient(app) as client:
        response = client.get("/api/v1/not-found")

    assert response.status_code == 404
    assert "server-ui" not in response.text
    assert response.headers["content-type"].startswith("application/json")
