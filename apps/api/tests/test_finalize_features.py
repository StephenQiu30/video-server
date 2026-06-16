from datetime import UTC, datetime
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.models import DownloadTask, User
from app.services.pdf import PDFService
from app.services.storage import ObjectStorage
from app.core.security import create_access_token
from video_downloader_shared.states import TaskState


def test_pdf_service_generates_report_bytes() -> None:
    # Arrange: Create a task with AI summary content
    task = DownloadTask(
        id="task-123",
        title="测试视频分析报告标题",
        updated_at=datetime.now(UTC),
        ai_summary="# AI 总结\n- 关键点 1\n- 关键点 2\n\n这是详细的报告段落内容。"
    )

    # Act: Generate the PDF report
    service = PDFService()
    pdf_bytes = service.generate_task_report(task)

    # Assert: Verify the PDF bytes are non-empty and have the correct magic header
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF-")


def test_export_task_pdf_endpoint_pending_returns_409(client: TestClient, session: Session) -> None:
    # Arrange: Create an authenticated user
    user = User(
        email="test_pdf_pending@example.com",
        display_name="Test Pending User",
        github_id="github-pending-123",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(user.id)

    # Create a queued (pending) task owned by the user
    task = DownloadTask(
        id="task-pending-pdf",
        user_id=user.id,
        state=TaskState.QUEUED.value,
        title="Pending Task Title",
        updated_at=datetime.now(UTC),
        source_url="https://bilibili.com/video/BV1xx"
    )
    session.add(task)
    session.commit()

    # Act: Request the PDF for a pending task
    response = client.get(
        f"/api/tasks/{task.id}/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert: Verify it returns 409 Conflict
    assert response.status_code == 409
    json_data = response.json()
    assert json_data["error"]["code"] == "invalid_state"
    assert "任务尚未完成" in json_data["error"]["message"]


def test_export_task_pdf_endpoint_success(client: TestClient, session: Session) -> None:
    # Arrange: Create an authenticated user
    user = User(
        email="test_pdf_success@example.com",
        display_name="Test Success User",
        github_id="github-success-123",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(user.id)

    # Create a succeeded task owned by the user with AI summary
    task = DownloadTask(
        id="task-success-pdf",
        user_id=user.id,
        state=TaskState.SUCCEEDED.value,
        title="Succeeded Task Title",
        updated_at=datetime.now(UTC),
        source_url="https://bilibili.com/video/BV2xx",
        ai_summary="# Succeeded Summary\n- Bullet 1"
    )
    session.add(task)
    session.commit()

    # Act: Request the PDF for the completed task
    response = client.get(
        f"/api/tasks/{task.id}/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert: Verify 200 OK and PDF file responses
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")


def test_export_task_pdf_endpoint_non_owner_returns_404(client: TestClient, session: Session) -> None:
    # Arrange: Create the task owner
    owner = User(
        email="pdf_owner@example.com",
        display_name="PDF Owner",
        github_id="github-pdf-owner-123",
    )
    session.add(owner)
    session.commit()
    session.refresh(owner)

    # Create a different user (non-owner)
    other_user = User(
        email="pdf_other@example.com",
        display_name="PDF Other User",
        github_id="github-pdf-other-123",
    )
    session.add(other_user)
    session.commit()
    session.refresh(other_user)

    other_token = create_access_token(other_user.id)

    # Create a succeeded task owned by the first user
    task = DownloadTask(
        id="task-pdf-nonowner",
        user_id=owner.id,
        state=TaskState.SUCCEEDED.value,
        title="Owner Task Title",
        updated_at=datetime.now(UTC),
        source_url="https://bilibili.com/video/BV4xx",
        ai_summary="# Summary\n- Point 1"
    )
    session.add(task)
    session.commit()

    # Act: Non-owner requests the PDF
    response = client.get(
        f"/api/tasks/{task.id}/pdf",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    # Assert: Verify it returns 404 (task not found for this user)
    assert response.status_code == 404
    json_data = response.json()
    assert json_data["error"]["code"] == "not_found"


def test_task_download_link_returns_presigned_url_and_ttl(client: TestClient, session: Session, monkeypatch) -> None:
    # Arrange: Create a succeeded task with object key
    user = User(
        email="test_download_link@example.com",
        display_name="Test Download Link User",
        github_id="github-download-link-123",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(user.id)

    task = DownloadTask(
        id="task-download-link-1",
        user_id=user.id,
        state=TaskState.SUCCEEDED.value,
        title="Download Link Task",
        source_url="https://bilibili.com/video/BV2xx",
        object_key="object-key-1",
    )
    session.add(task)
    session.commit()

    monkeypatch.setattr(
        ObjectStorage,
        "presign_download_url",
        lambda self, object_key: f"https://mock-storage/{object_key}",
    )

    # Act: Request temporary download link
    response = client.get(
        f"/api/tasks/{task.id}/download-link",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Assert: verify link and TTL
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://mock-storage/object-key-1"
    assert data["expires_in_seconds"] == 900


@pytest.mark.anyio
async def test_stream_tasks_sse_endpoint(session: Session) -> None:
    # Arrange: Create an authenticated user
    user = User(
        email="test_sse@example.com",
        display_name="Test SSE User",
        github_id="github-sse-123",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Add a task to verify it is returned in the stream
    task = DownloadTask(
        id="task-sse-1",
        user_id=user.id,
        state=TaskState.QUEUED.value,
        title="SSE Task Title",
        updated_at=datetime.now(UTC),
        source_url="https://bilibili.com/video/BV3xx"
    )
    session.add(task)
    session.commit()

    # Act & Assert: Call the router stream_tasks and advance generator within the patched session context
    from app.routers.tasks import stream_tasks
    with patch("app.routers.tasks.SessionLocal", return_value=session):
        response = await stream_tasks(current_user=user)

        # Assert: Verify response metadata
        assert response.media_type == "text/event-stream"
        assert response.headers["Cache-Control"] == "no-cache"

        # Get the async generator from the response body iterator
        generator = response.body_iterator
        
        # Advance the generator exactly once to read the first event
        first_event = await generator.__anext__()
        assert first_event.startswith("event: tasks")
        assert "SSE Task Title" in first_event


@pytest.mark.anyio
async def test_stream_tasks_calls_cleanup_expired_outputs(session: Session) -> None:
    """stream_tasks must call cleanup_expired_task_outputs before emitting events."""
    user = User(
        email="stream_cleanup@example.com",
        display_name="Stream Cleanup User",
        github_id="github-stream-cleanup",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    task = DownloadTask(
        id="task-stream-cleanup-1",
        user_id=user.id,
        state=TaskState.QUEUED.value,
        title="Stream Cleanup Task",
        updated_at=datetime.now(UTC),
        source_url="https://bilibili.com/video/BV4xx",
    )
    session.add(task)
    session.commit()

    call_log = []

    def fake_cleanup(db):
        call_log.append("called")

    from app.routers.tasks import stream_tasks

    with (
        patch("app.routers.tasks.SessionLocal", return_value=session),
        patch("app.routers.tasks.cleanup_expired_task_outputs", side_effect=fake_cleanup),
    ):
        response = await stream_tasks(current_user=user)
        generator = response.body_iterator
        _ = await generator.__anext__()

    assert call_log, "cleanup_expired_task_outputs was not called by stream_tasks"
