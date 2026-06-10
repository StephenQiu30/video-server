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
    """Full task lifecycle: create, list, detail, events, cancel, retry."""
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
    """Cross-user access returns 404; expired download link returns 410."""
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


def test_succeeded_task_exposes_state_progress_and_download_fields(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """SUCCEEDED task response includes state, progress, output_filename, object_size, and expires_at."""
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)

    owner = _make_user(session, email="succeeded@example.com", github_id="succeeded-owner")
    token = create_access_token(owner.id)
    headers = {"Authorization": f"Bearer {token}"}

    task = DownloadTask(
        user_id=owner.id,
        source_url="https://bilibili.com/video/BV1xx411c7d",
        title="downloaded-video",
        state=TaskState.SUCCEEDED.value,
        progress=100,
        output_filename="downloaded-video.mp4",
        object_key="users/1/tasks/abc/downloaded-video.mp4",
        object_size=1024000,
        expires_at=(datetime.now(UTC) + timedelta(hours=24)),
    )
    session.add(task)
    session.commit()

    response = client.get(f"/api/tasks/{task.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == TaskState.SUCCEEDED.value
    assert body["progress"] == 100
    assert body["output_filename"] == "downloaded-video.mp4"
    assert body["object_size"] == 1024000
    assert body["expires_at"] is not None


def test_download_link_returns_presigned_url_for_owner(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """/api/tasks/{id}/download-link returns presigned url and expires_in_seconds for owner."""
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)

    owner = _make_user(session, email="dl-owner@example.com", github_id="dl-owner")
    token = create_access_token(owner.id)
    headers = {"Authorization": f"Bearer {token}"}

    task = DownloadTask(
        user_id=owner.id,
        source_url="https://bilibili.com/video/BV1xx411c7d",
        title="presigned-test",
        state=TaskState.SUCCEEDED.value,
        progress=100,
        object_key="users/1/tasks/abc/video.mp4",
        object_size=500000,
        expires_at=(datetime.now(UTC) + timedelta(hours=12)),
    )
    session.add(task)
    session.commit()

    fake_url = "https://s3.example.com/bucket/key?X-Amz-Signature=abc123&X-Amz-Expires=900"
    monkeypatch.setattr(
        "app.services.storage.ObjectStorage.presign_download_url",
        lambda self, object_key: fake_url,
    )

    response = client.get(f"/api/tasks/{task.id}/download-link", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["url"] == fake_url
    assert body["expires_in_seconds"] > 0


def test_parse_api_requires_auth(client: TestClient) -> None:
    """/api/parse rejects unauthenticated requests with 401."""
    response = client.post(
        "/api/parse",
        json={"url": "https://bilibili.com/video/BV1xx411c7d"},
    )
    assert response.status_code == 401


def test_create_task_rejects_unsafe_host_before_enqueue(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """Restricted host URLs (.invalid TLD) are rejected with unsafe_url before enqueue."""
    def fail_enqueue(_: str) -> None:
        raise AssertionError("unsafe host should not be enqueued")

    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", fail_enqueue)
    user = _make_user(session, email="unsafe-host@example.com", github_id="unsafe-host-user")
    token = create_access_token(user.id)

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://example.invalid/video/1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsafe_url"


def test_create_task_accepts_known_bilibili_platform_before_enqueue(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """Known Bilibili URLs are accepted and enqueued successfully."""
    enqueued = []
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: enqueued.append(task_id))
    user = _make_user(session, email="known-platform@example.com", github_id="known-platform-user")
    token = create_access_token(user.id)

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert response.status_code == 201
    assert enqueued == [response.json()["id"]]


def test_create_task_rate_limits_authenticated_user(monkeypatch, client: TestClient, session: Session) -> None:
    """Rate limiter rejects second task creation within the same window."""
    from app.services.rate_limit import InMemoryRateLimiter

    enqueued = []
    limiter = InMemoryRateLimiter(1, 60)
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: enqueued.append(task_id))
    monkeypatch.setattr("app.routers.tasks.get_create_task_rate_limiter", lambda: limiter)
    user = _make_user(session, email="task-rate@example.com", github_id="task-rate-user")
    token = create_access_token(user.id)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/api/tasks",
        headers=headers,
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )
    second = client.post(
        "/api/tasks",
        headers=headers,
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"


def test_task_list_state_filter_invalid(session: Session, client: TestClient) -> None:
    """Invalid state filter returns 422 with invalid_state error code."""
    user = _make_user(session, email="filter@example.com", github_id="filter-user")
    token = create_access_token(user.id)

    response = client.get("/api/tasks?state=not-exist", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_state"


def test_create_task_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/tasks",
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD", "title": "no-auth"},
    )
    assert response.status_code == 401


def test_create_task_rejects_daily_quota_exceeded(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)
    user = _make_user(session, email="daily-quota@example.com", github_id="daily-quota-user")
    user.daily_task_quota = 0
    session.commit()
    token = create_access_token(user.id)

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "limit_exceeded"


def test_create_task_rejects_storage_quota_exceeded(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)
    user = _make_user(session, email="storage-quota@example.com", github_id="storage-quota-user")
    user.storage_quota_bytes = 0
    session.commit()
    token = create_access_token(user.id)

    # Seed a task with object_size so storage_used >= storage_quota_bytes
    task = DownloadTask(
        user_id=user.id,
        source_url="https://bilibili.com/video/BV1xx411c7d",
        title="storage-seed",
        state=TaskState.SUCCEEDED.value,
        object_key="bucket/user/video.mp4",
        object_size=1024,
    )
    session.add(task)
    session.commit()

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "limit_exceeded"


def test_create_task_rejects_concurrent_task_limit(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)
    user = _make_user(session, email="concurrent@example.com", github_id="concurrent-user")
    user.concurrent_task_quota = 1
    session.commit()
    token = create_access_token(user.id)

    # Seed an active (queued) task to exhaust the concurrency slot
    active_task = DownloadTask(
        user_id=user.id,
        source_url="https://bilibili.com/video/BV1xx411c7d",
        title="active-seed",
        state=TaskState.QUEUED.value,
    )
    session.add(active_task)
    session.commit()

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "limit_exceeded"


def test_error_responses_do_not_leak_sensitive_params(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """Error responses must not contain cookie, token, or secret values."""
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)
    user = _make_user(session, email="leak-check@example.com", github_id="leak-check-user")
    token = create_access_token(user.id)

    response = client.post(
        "/api/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://example.invalid/video/1"},
    )

    assert response.status_code == 422
    body = response.text.lower()
    for secret in ("cookie", "token", "secret", "password", "minioadmin"):
        assert secret not in body, f"Sensitive param '{secret}' leaked in error response"
