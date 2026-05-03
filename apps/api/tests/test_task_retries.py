from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import AppError
from app.db.base import Base
from app.models import DownloadTask, User
from app.services.tasks import annotate_latest_attempts, retry_task
from video_downloader_shared.states import TaskState


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _user(db) -> User:
    user = User(
        email="local@example.com",
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


def test_retry_task_links_new_attempt_to_previous_task() -> None:
    db = _db_session()
    user = _user(db)
    failed = _task(db, user, TaskState.FAILED)

    retried = retry_task(db, user, failed)

    assert retried.retry_of_task_id == failed.id
    assert retried.attempt_no == 2
    assert retried.state == TaskState.QUEUED.value

    annotate_latest_attempts(db, [failed, retried])
    assert failed.is_latest_attempt is False
    assert retried.is_latest_attempt is True


def test_retry_task_rejects_active_task() -> None:
    db = _db_session()
    user = _user(db)
    running = _task(db, user, TaskState.RUNNING)

    try:
        retry_task(db, user, running)
    except AppError as exc:
        assert exc.status_code == 409
        assert exc.code == "invalid_state"
    else:
        raise AssertionError("expected active task retry to be rejected")


def test_retry_task_rejects_superseded_attempt() -> None:
    db = _db_session()
    user = _user(db)
    failed = _task(db, user, TaskState.FAILED)
    retry_task(db, user, failed)

    try:
        retry_task(db, user, failed)
    except AppError as exc:
        assert exc.status_code == 409
        assert exc.code == "retry_superseded"
    else:
        raise AssertionError("expected old retry attempt to be rejected")


def test_retry_task_allows_expired_successful_task() -> None:
    db = _db_session()
    user = _user(db)
    expired = _task(
        db,
        user,
        TaskState.SUCCEEDED,
        object_key="users/1/tasks/task-1/video.mp4",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    retried = retry_task(db, user, expired)

    assert retried.retry_of_task_id == expired.id
    assert retried.attempt_no == 2
