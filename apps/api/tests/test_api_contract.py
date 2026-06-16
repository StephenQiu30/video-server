from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User
from app.services.rate_limit import InMemoryRateLimiter


def _make_user(session: Session) -> User:
    user = User(email="parse-contract@example.com", display_name="Parse Contract", github_id="parse-contract")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_api_only_backend_not_serving_spa(client: TestClient) -> None:
    # API 服务只提供 API/健康检查，不承接前端 SPA 回退路由
    response = client.get("/workbench")

    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "not_found"


def test_app_error_uses_unified_failure_envelope(client: TestClient, session: Session) -> None:
    user = _make_user(session)
    token = create_access_token(user.id)

    response = client.get(
        "/api/tasks?state=not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "error": {
            "code": "invalid_state",
            "message": "任务状态筛选值无效",
            "details": None,
        },
    }


def test_validation_error_uses_unified_failure_envelope(client: TestClient, session: Session) -> None:
    user = _make_user(session)
    token = create_access_token(user.id)

    response = client.post(
        "/api/parse",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": ""},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


def test_unknown_exception_uses_safe_failure_envelope() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.main import create_app

    app: FastAPI = create_app()

    @app.get("/api/_boom")
    def boom() -> None:
        raise RuntimeError("database password leaked")

    response = TestClient(app, raise_server_exceptions=False).get("/api/_boom")

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "error": {
            "code": "internal_error",
            "message": "服务暂时不可用，请稍后重试",
            "details": None,
        },
    }


def test_parse_response_includes_platform_metadata(monkeypatch, client: TestClient, session: Session) -> None:
    def fake_extract(url: str) -> dict:
        return {
            "title": "Douyin contract sample",
            "duration": 12,
            "extractor_key": "Douyin",
            "formats": [
                {
                    "format_id": "http-720",
                    "height": 720,
                    "width": 1280,
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                }
            ],
        }

    monkeypatch.setattr("app.sources.adapters.ytdlp._extract_with_ytdlp", fake_extract)
    user = _make_user(session)
    token = create_access_token(user.id)

    response = client.post(
        "/api/parse",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://www.douyin.com/video/123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["platform_id"] == "douyin"
    assert data["platform_category"] == "cn-short-video"
    assert data["compliance_note"]
    assert data["source_site"] == "抖音"
    assert data["formats"]


def test_parse_requires_authenticated_user(client: TestClient) -> None:
    response = client.post("/api/parse", json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"})

    assert response.status_code == 401


def test_parse_rate_limits_authenticated_user(monkeypatch, client: TestClient, session: Session) -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    monkeypatch.setattr("app.routers.parse.get_parse_rate_limiter", lambda: limiter)
    monkeypatch.setattr(
        "app.sources.adapters.ytdlp._extract_with_ytdlp",
        lambda url: {
            "title": "Rate limit sample",
            "extractor_key": "BiliBili",
            "formats": [{"format_id": "best", "height": 720, "ext": "mp4", "vcodec": "h264"}],
        },
    )
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/api/parse", headers=headers, json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"})
    second = client.post("/api/parse", headers=headers, json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"
