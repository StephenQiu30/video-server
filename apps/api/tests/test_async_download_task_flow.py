"""Tests for the async download task flow OpenSpec compliance.

Covers: expired state, cleanup_expired_task_outputs, full lifecycle,
reconcile_stale_active_tasks, error code stability, and state transition rules.
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import DownloadTask, TaskEvent, User
from app.services.tasks import (
    cancel_task,
    cleanup_expired_task_outputs,
    list_task_events,
    reconcile_stale_active_tasks,
    retry_task,
)
from video_downloader_shared.states import TaskState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _user(db) -> User:
    user = User(
        email="flow@example.com",
        password_hash="x",
        daily_task_quota=10,
        concurrent_task_quota=1,
        max_file_size_bytes=2_147_483_648,
        file_retention_hours=24,
        storage_quota_bytes=5_368_709_120,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _task(db, user: User, state: TaskState, **kwargs) -> DownloadTask:
    task = DownloadTask(
        user_id=user.id,
        source_url="https://example.com/video",
        title="Sample",
        format_id="best",
        state=state.value,
        progress=0,
        **kwargs,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# TaskState.EXPIRED enum value
# ---------------------------------------------------------------------------


def test_task_state_expired_enum_exists():
    """TaskState must include EXPIRED to represent artifact cleanup."""
    assert hasattr(TaskState, "EXPIRED")
    assert TaskState.EXPIRED.value == "expired"


def test_task_state_has_exactly_six_values():
    """PRD03 defines exactly six task states."""
    assert len(TaskState) == 6
    expected = {"queued", "running", "succeeded", "failed", "canceled", "expired"}
    assert {s.value for s in TaskState} == expected


# ---------------------------------------------------------------------------
# cleanup_expired_task_outputs
# ---------------------------------------------------------------------------


def test_cleanup_expired_task_outputs_transitions_to_expired(monkeypatch):
    """Expired SUCCEEDED tasks should transition to EXPIRED state."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.SUCCEEDED,
        object_key="users/1/tasks/abc/video.mp4",
        object_size=1024,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )

    monkeypatch.setattr(
        "app.services.tasks.ObjectStorage",
        lambda: MagicMock(delete_object=MagicMock()),
    )

    removed = cleanup_expired_task_outputs(db)

    assert removed == 1
    db.refresh(task)
    assert task.state == TaskState.EXPIRED.value
    assert task.object_key is None
    assert task.failure_code == "retention_expired"


def test_cleanup_expired_task_outputs_clears_object_key(monkeypatch):
    """After cleanup, object_key must be None."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.SUCCEEDED,
        object_key="bucket/video.mp4",
        object_size=500,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    monkeypatch.setattr(
        "app.services.tasks.ObjectStorage",
        lambda: MagicMock(delete_object=MagicMock()),
    )

    cleanup_expired_task_outputs(db)
    db.refresh(task)

    assert task.object_key is None


def test_cleanup_expired_task_outputs_records_event(monkeypatch):
    """Cleanup must write a task_event for the state change."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.SUCCEEDED,
        object_key="bucket/video.mp4",
        object_size=500,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    monkeypatch.setattr(
        "app.services.tasks.ObjectStorage",
        lambda: MagicMock(delete_object=MagicMock()),
    )

    cleanup_expired_task_outputs(db)

    events = list_task_events(db, task)
    assert any(e.state == TaskState.EXPIRED.value for e in events)


def test_cleanup_expired_task_outputs_skips_non_expired():
    """Tasks within retention period must not be touched."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.SUCCEEDED,
        object_key="bucket/video.mp4",
        object_size=500,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )

    removed = cleanup_expired_task_outputs(db)

    assert removed == 0
    db.refresh(task)
    assert task.state == TaskState.SUCCEEDED.value
    assert task.object_key == "bucket/video.mp4"


def test_cleanup_expired_task_outputs_skips_already_expired():
    """Tasks already in expired state must not be processed again."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.EXPIRED,
        object_key=None,
        failure_code="retention_expired",
    )

    removed = cleanup_expired_task_outputs(db)

    assert removed == 0


# ---------------------------------------------------------------------------
# reconcile_stale_active_tasks
# ---------------------------------------------------------------------------


def test_reconcile_stale_active_tasks_fails_stale_running(monkeypatch):
    """Stale RUNNING tasks should be auto-failed with task_timeout."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.RUNNING,
        updated_at=datetime.now(UTC) - timedelta(hours=2),
    )

    monkeypatch.setattr(
        "app.services.tasks.get_settings",
        lambda: MagicMock(max_task_runtime_seconds=3600),
    )

    reconciled = reconcile_stale_active_tasks(db)

    assert reconciled == 1
    db.refresh(task)
    assert task.state == TaskState.FAILED.value
    assert task.failure_code == "task_timeout"


def test_reconcile_stale_active_tasks_fails_stale_queued(monkeypatch):
    """Stale QUEUED tasks should be auto-failed."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.QUEUED,
        updated_at=datetime.now(UTC) - timedelta(hours=2),
    )

    monkeypatch.setattr(
        "app.services.tasks.get_settings",
        lambda: MagicMock(max_task_runtime_seconds=3600),
    )

    reconciled = reconcile_stale_active_tasks(db)

    assert reconciled == 1
    db.refresh(task)
    assert task.state == TaskState.FAILED.value


def test_reconcile_stale_active_tasks_skips_fresh_tasks(monkeypatch):
    """Tasks within runtime limit must not be failed."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.RUNNING,
        updated_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    monkeypatch.setattr(
        "app.services.tasks.get_settings",
        lambda: MagicMock(max_task_runtime_seconds=3600),
    )

    reconciled = reconcile_stale_active_tasks(db)

    assert reconciled == 0
    db.refresh(task)
    assert task.state == TaskState.RUNNING.value


# ---------------------------------------------------------------------------
# Cancel / retry state rules
# ---------------------------------------------------------------------------


def test_cancel_rejects_succeeded_task():
    """Cancel on succeeded task must be rejected."""
    db = _db_session()
    user = _user(db)
    task = _task(db, user, TaskState.SUCCEEDED, object_key="bucket/v.mp4")

    try:
        cancel_task(db, task)
    except Exception as exc:
        assert exc.code == "invalid_state"
    else:
        raise AssertionError("expected cancel on succeeded to be rejected")


def test_cancel_rejects_expired_task():
    """Cancel on expired task must be rejected."""
    db = _db_session()
    user = _user(db)
    task = _task(db, user, TaskState.EXPIRED)

    try:
        cancel_task(db, task)
    except Exception as exc:
        assert exc.code == "invalid_state"
    else:
        raise AssertionError("expected cancel on expired to be rejected")


def test_retry_allows_expired_task():
    """Expired tasks should be retryable."""
    db = _db_session()
    user = _user(db)
    task = _task(
        db,
        user,
        TaskState.EXPIRED,
        failure_code="retention_expired",
    )

    retried = retry_task(db, user, task)

    assert retried.retry_of_task_id == task.id
    assert retried.state == TaskState.QUEUED.value
    assert retried.attempt_no == 2


# ---------------------------------------------------------------------------
# Error code stability
# ---------------------------------------------------------------------------


def test_worker_failure_code_enum_values_are_stable():
    """WorkerFailureCode enum values must match the canonical string set."""
    from worker.domain import WorkerFailureCode

    expected = {
        "download_failed",
        "format_unavailable",
        "file_too_large",
        "media_tools_missing",
        "ffprobe_failed",
        "storage_failed",
        "task_timeout",
        "task_canceled",
        "platform_restricted",
        "platform_rate_limited",
        "unsupported_platform",
        "browser_cookies_unavailable",
    }
    actual = {code.value for code in WorkerFailureCode}
    assert actual == expected


def test_failure_code_classifies_known_exceptions():
    """failure_code() must map known exception patterns to correct enum values."""
    from worker.domain import WorkerFailureCode
    from worker.failures import failure_code

    cases = [
        ("ERROR: requested format is not available", WorkerFailureCode.FORMAT_UNAVAILABLE),
        ("ERROR: file is larger than max-filesize", WorkerFailureCode.FILE_TOO_LARGE),
        ("ERROR: job timed out", WorkerFailureCode.TASK_TIMEOUT),
        ("ERROR: unsupported URL", WorkerFailureCode.UNSUPPORTED_PLATFORM),
        ("ERROR: cookiesfrombrowser keyring access denied", WorkerFailureCode.BROWSER_COOKIES_UNAVAILABLE),
        ("some generic download error", WorkerFailureCode.DOWNLOAD_FAILED),
    ]
    for message, expected_code in cases:
        result = failure_code(RuntimeError(message))
        assert result == expected_code, f"Expected {expected_code} for '{message}', got {result}"
