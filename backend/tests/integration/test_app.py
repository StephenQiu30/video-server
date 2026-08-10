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
    next_assets = dist / "_next" / "static" / "chunks"
    assets.mkdir(parents=True)
    next_assets.mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><title>server-ui</title><div id='root'></div>",
        encoding="utf-8",
    )
    (dist / "404.html").write_text(
        "<!doctype html><title>not-found</title>", encoding="utf-8"
    )
    (assets / "app.js").write_text("window.SERVER_UI = true;", encoding="utf-8")
    (next_assets / "app.123.js").write_text("window.NEXT_UI = true;", encoding="utf-8")
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


def test_frontend_is_same_origin_and_redirects_legacy_download_route(
    tmp_path: Path,
) -> None:
    dist = build_dist(tmp_path)
    detail = dist / "downloads" / "detail"
    detail.mkdir(parents=True)
    (detail / "index.html").write_text(
        "<!doctype html><title>download-detail</title>", encoding="utf-8"
    )
    app = create_app(Settings(app_env="test", frontend_dist_dir=dist))

    with TestClient(app) as client:
        index = client.get("/")
        legacy = client.get("/downloads/123", follow_redirects=False)
        detail_page = client.get("/downloads/detail?jobId=123")
        asset = client.get("/assets/app.js")
        next_asset = client.get("/_next/static/chunks/app.123.js")

    assert index.status_code == 200
    assert "server-ui" in index.text
    assert legacy.status_code == 308
    assert legacy.headers["location"] == "/downloads/detail?jobId=123"
    assert detail_page.status_code == 200
    assert "download-detail" in detail_page.text
    assert asset.text == "window.SERVER_UI = true;"
    assert index.headers["cache-control"] == "no-store, max-age=0"
    assert detail_page.headers["cache-control"] == "no-store, max-age=0"
    assert next_asset.headers["cache-control"] == (
        "public, max-age=31536000, immutable"
    )


def test_directory_route_serves_index_directly_without_redirect(tmp_path: Path) -> None:
    # Next.js static export emits route directories. A refresh of /history must
    # return the page directly, not a trailing-slash redirect.
    dist = build_dist(tmp_path)
    (dist / "history").mkdir()
    (dist / "history" / "index.html").write_text(
        "<!doctype html><title>server-history</title><div id='root'></div>",
        encoding="utf-8",
    )
    app = create_app(Settings(app_env="test", frontend_dist_dir=dist))

    with TestClient(app) as client:
        response = client.get("/history", follow_redirects=False)

    assert response.status_code == 200
    assert "server-history" in response.text
    assert response.headers["cache-control"] == "no-store, max-age=0"


def test_unknown_ui_route_returns_exported_404(tmp_path: Path) -> None:
    dist = build_dist(tmp_path)
    app = create_app(Settings(app_env="test", frontend_dist_dir=dist))

    with TestClient(app) as client:
        response = client.get("/missing-page")

    assert response.status_code == 404
    assert "not-found" in response.text
    assert response.headers["cache-control"] == "no-store, max-age=0"


def test_unknown_api_never_falls_back_to_frontend(tmp_path: Path) -> None:
    dist = build_dist(tmp_path)
    app = create_app(Settings(app_env="test", frontend_dist_dir=dist))

    with TestClient(app) as client:
        response = client.get("/api/not-found")

    assert response.status_code == 404
    assert "server-ui" not in response.text
    assert response.headers["content-type"].startswith("application/json")
