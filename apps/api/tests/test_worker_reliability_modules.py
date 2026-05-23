from pathlib import Path

import pytest

from app.models import DownloadTask, User
from video_downloader_shared.states import TaskState


def _user(session) -> User:
    user = User(
        email="worker-reliability@example.com",
        password_hash="x",
        daily_task_quota=10,
        concurrent_task_quota=1,
        max_file_size_bytes=2_147_483_648,
        file_retention_hours=24,
        storage_quota_bytes=5_368_709_120,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _task(session, user: User, state: TaskState, **kwargs) -> DownloadTask:
    task = DownloadTask(
        user_id=user.id,
        source_url="https://example.com/video",
        title="Sample",
        format_id="best",
        state=state.value,
        progress=0,
        **kwargs,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def test_download_runner_resolves_latest_output_path(tmp_path: Path) -> None:
    from worker.download_runner import resolve_output_path

    first = tmp_path / "video.f137.mp4"
    second = tmp_path / "video.mp4"
    first.write_text("old")
    second.write_text("latest")
    first.touch()
    second.touch()

    assert resolve_output_path(tmp_path, tmp_path / "missing.webm") == second


def test_failure_mapper_returns_typed_failure_info() -> None:
    from worker.domain import WorkerFailureCode, WorkerStage
    from worker.failures import failure_info_from_exception

    info = failure_info_from_exception(
        RuntimeError("ERROR: requested format is not available"),
        WorkerStage.DOWNLOAD,
    )

    assert info.code == WorkerFailureCode.FORMAT_UNAVAILABLE
    assert info.stage == WorkerStage.DOWNLOAD
    assert info.retryable is False
    assert "清晰度" in info.reason


def test_ai_pipeline_skips_when_keys_are_missing(monkeypatch, session, tmp_path: Path) -> None:
    from app.core.config import get_settings
    from worker.ai_pipeline import process_ai_pipeline
    from worker.domain import AIProcessStatus, DownloadArtifact

    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("TRANSCRIPTION_API_KEY", raising=False)
    get_settings.cache_clear()
    user = _user(session)
    task = _task(session, user, TaskState.SUCCEEDED)
    artifact = DownloadArtifact(path=tmp_path / "video.mp4", filename="video.mp4", size_bytes=1)
    artifact.path.write_bytes(b"video")

    result = process_ai_pipeline(session, task, artifact)

    assert result.status == AIProcessStatus.SKIPPED
    assert task.ai_status == AIProcessStatus.SKIPPED.value
    get_settings.cache_clear()


def test_process_download_task_skips_existing_success_without_downloading(monkeypatch, session) -> None:
    from worker import jobs

    user = _user(session)
    task = _task(
        session,
        user,
        TaskState.SUCCEEDED,
        object_key="users/1/tasks/task/video.mp4",
    )

    class SessionFactory:
        def __call__(self):
            return session

    monkeypatch.setattr(jobs, "SessionLocal", SessionFactory())
    monkeypatch.setattr(jobs, "_mark_running", lambda *_: pytest.fail("should not re-run succeeded task"))

    jobs.process_download_task(task.id)

    assert task.state == TaskState.SUCCEEDED.value


def test_process_download_task_skips_canceled_without_downloading(monkeypatch, session) -> None:
    from worker import jobs

    user = _user(session)
    task = _task(session, user, TaskState.CANCELED)

    class SessionFactory:
        def __call__(self):
            return session

    monkeypatch.setattr(jobs, "SessionLocal", SessionFactory())
    monkeypatch.setattr(jobs, "_mark_running", lambda *_: pytest.fail("should not run canceled task"))

    jobs.process_download_task(task.id)

    assert task.state == TaskState.CANCELED.value
