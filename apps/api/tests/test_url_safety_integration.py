"""API-level URL safety integration tests.

PRD01 / PLAN01 验收：API 不会把危险地址加入任务队列。
这些测试验证 /api/tasks 和 /api/parse 端点在接收危险 URL 时返回 422 错误。
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import User


def _make_user(session: Session) -> User:
    user = User(email="url-safety@example.com", display_name="URL Safety", github_id="url-safety")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# --- /api/tasks: 危险 URL 应被拒绝，不创建任务 ---


def test_tasks_api_rejects_localhost(client: TestClient, session: Session) -> None:
    """POST /api/tasks 带 localhost URL 应返回 422，不创建任务。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/tasks", headers=headers, json={"url": "http://localhost/video"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "invalid_url"


def test_tasks_api_rejects_private_ip(client: TestClient, session: Session) -> None:
    """POST /api/tasks 带内网 IP 应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    for host in ["10.0.0.1", "172.16.0.1", "192.168.1.1"]:
        response = client.post(
            "/api/tasks", headers=headers, json={"url": f"http://{host}/video"}
        )
        assert response.status_code == 422, f"host={host} should be rejected"
        assert response.json()["error"]["code"] == "invalid_url"


def test_tasks_api_rejects_loopback_ip(client: TestClient, session: Session) -> None:
    """POST /api/tasks 带 127.x 回环地址应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/tasks", headers=headers, json={"url": "http://127.0.0.1/video"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_url"


def test_tasks_api_rejects_non_http_scheme(client: TestClient, session: Session) -> None:
    """POST /api/tasks 带非 http/https 协议应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    for scheme_url in ["ftp://example.com/video", "file:///etc/passwd"]:
        response = client.post("/api/tasks", headers=headers, json={"url": scheme_url})
        assert response.status_code == 422, f"url={scheme_url} should be rejected"


def test_tasks_api_rejects_empty_url(client: TestClient, session: Session) -> None:
    """POST /api/tasks 带空 URL 应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/tasks", headers=headers, json={"url": ""})

    assert response.status_code == 422


def test_tasks_api_rejects_plain_text(client: TestClient, session: Session) -> None:
    """POST /api/tasks 带非 URL 文本应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/tasks", headers=headers, json={"url": "not a url at all"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_url"


def test_tasks_api_accepts_public_url(client: TestClient, session: Session, monkeypatch) -> None:
    """POST /api/tasks 带公网 URL 应正常创建任务。"""
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/tasks", headers=headers, json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"}
    )

    assert response.status_code == 201


# --- /api/parse: 危险 URL 应被拒绝 ---


def test_parse_api_rejects_localhost(client: TestClient, session: Session) -> None:
    """POST /api/parse 带 localhost URL 应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/parse", headers=headers, json={"url": "http://localhost/video"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_url"


def test_parse_api_rejects_private_ip(client: TestClient, session: Session) -> None:
    """POST /api/parse 带内网 IP 应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/parse", headers=headers, json={"url": "http://192.168.1.1/video"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_url"


def test_parse_api_rejects_reserved_ip(client: TestClient, session: Session) -> None:
    """POST /api/parse 带保留地址应返回 422。"""
    user = _make_user(session)
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/parse", headers=headers, json={"url": "http://0.0.0.0/video"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_url"
