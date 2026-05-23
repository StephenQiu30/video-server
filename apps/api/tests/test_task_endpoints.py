from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import DownloadTask, User
from app.core.security import create_access_token
from video_downloader_shared.states import TaskState


def _make_user(session: Session, *, email: str, github_id: str) -> User:
    user = User(email=email, display_name=f"{email.split('@')[0]}", github_id=github_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_task_api_flow_coverage_taskread_fields_and_cancel_retry(monkeypatch, client: TestClient, session: Session) -> None:
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)

    owner = _make_user(session, email="task-api@example.com", github_id="task-api-owner")
    token = create_access_token(owner.id)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/tasks",
        headers=headers,
        json={
            "url": "v.douyin.com/test-short-video-id",
            "title": "任务流测试视频",
            "format_label": "推荐下载",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()

    assert created["state"] == TaskState.QUEUED.value
    assert created["source_url"] == "https://v.douyin.com/test-short-video-id"
    assert created["attempt_no"] == 1
    assert created["is_latest_attempt"] is True
    assert created["user_id"] == owner.id
    assert created["format_label"] == "推荐下载"
    task_id = created["id"]

    list_response = client.get("/api/tasks", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["id"] == task_id

    detail_response = client.get(f"/api/tasks/{task_id}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["is_latest_attempt"] is True

    events_response = client.get(f"/api/tasks/{task_id}/events", headers=headers)
    assert events_response.status_code == 200
    events = events_response.json()
    assert events
    assert events[0]["task_id"] == task_id
    assert events[0]["state"] == TaskState.QUEUED.value

    cancel_response = client.post(f"/api/tasks/{task_id}/cancel", headers=headers)
    assert cancel_response.status_code == 200
    assert cancel_response.json()["state"] == TaskState.CANCELED.value

    retry_response = client.post(f"/api/tasks/{task_id}/retry", headers=headers)
    assert retry_response.status_code == 201
    retried = retry_response.json()

    assert retried["retry_of_task_id"] == task_id
    assert retried["attempt_no"] == 2
    assert retried["state"] == TaskState.QUEUED.value


def test_task_endpoints_cross_user_boundary_and_download_link_expired_or_miss(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)

    owner = _make_user(session, email="owner@example.com", github_id="task-boundary-owner")
    attacker = _make_user(session, email="attacker@example.com", github_id="task-boundary-attacker")
    owner_token = create_access_token(owner.id)
    attacker_token = create_access_token(attacker.id)

    task = DownloadTask(
        user_id=owner.id,
        source_url="https://bilibili.com/video/BV1xx411c7d",
        title="private-task",
        state=TaskState.SUCCEEDED.value,
        object_key="bucket/owner/video.mp4",
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)),
    )
    session.add(task)
    session.commit()

    attacker_headers = {"Authorization": f"Bearer {attacker_token}"}
    forbidden_get = client.get(f"/api/tasks/{task.id}", headers=attacker_headers)
    assert forbidden_get.status_code == 404
    assert forbidden_get.json()["error"]["code"] == "not_found"

    forbidden_link = client.get(f"/api/tasks/{task.id}/download-link", headers=attacker_headers)
    assert forbidden_link.status_code == 404
    assert forbidden_link.json()["error"]["code"] == "not_found"

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    expired_response = client.get(f"/api/tasks/{task.id}/download-link", headers=owner_headers)
    assert expired_response.status_code == 410
    assert expired_response.json()["error"]["code"] == "retention_expired"


def test_parse_api_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/parse",
        json={"url": "https://bilibili.com/video/BV1xx411c7d"},
    )
    assert response.status_code == 401


def test_task_list_state_filter_invalid(session: Session, client: TestClient) -> None:
    user = _make_user(session, email="filter@example.com", github_id="filter-user")
    token = create_access_token(user.id)

    response = client.get("/api/tasks?state=not-exist", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_state"
