import os
import time
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
    import os
    import time

    from worker.download_runner import resolve_output_path

    first = tmp_path / "video.f137.mp4"
    second = tmp_path / "video.mp4"
    first.write_text("old")
    second.write_text("latest")
    # Ensure strictly different mtimes so max() is deterministic
    now = time.time()
    os.utime(first, (now - 2, now - 2))
    os.utime(second, (now, now))

    assert resolve_output_path(tmp_path, tmp_path / "missing.webm") == second


# ---------------------------------------------------------------------------
# build_cookie_args — browser cookie configuration tests
# ---------------------------------------------------------------------------


def test_build_cookie_args_chrome() -> None:
    from worker.download_runner import build_cookie_args

    assert build_cookie_args("chrome") == {"cookiesfrombrowser": ("chrome",)}


def test_build_cookie_args_firefox() -> None:
    from worker.download_runner import build_cookie_args

    assert build_cookie_args("firefox") == {"cookiesfrombrowser": ("firefox",)}


def test_build_cookie_args_edge() -> None:
    from worker.download_runner import build_cookie_args

    assert build_cookie_args("edge") == {"cookiesfrombrowser": ("edge",)}


def test_build_cookie_args_case_insensitive() -> None:
    from worker.download_runner import build_cookie_args

    assert build_cookie_args("CHROME") == {"cookiesfrombrowser": ("chrome",)}
    assert build_cookie_args("Firefox") == {"cookiesfrombrowser": ("firefox",)}
    assert build_cookie_args("  Edge  ") == {"cookiesfrombrowser": ("edge",)}


def test_build_cookie_args_invalid_browser_warns_and_returns_empty(caplog) -> None:
    from worker.download_runner import build_cookie_args

    with caplog.at_level("WARNING"):
        result = build_cookie_args("ie6")

    assert result == {}
    assert "ie6" in caplog.text


def test_build_cookie_args_unconfigured_returns_empty() -> None:
    from worker.download_runner import build_cookie_args

    assert build_cookie_args(None) == {}
    assert build_cookie_args("") == {}


def test_build_cookie_args_disabled_values() -> None:
    from worker.download_runner import build_cookie_args

    for val in ("none", "false", "off"):
        assert build_cookie_args(val) == {}, f"expected empty for '{val}'"


def test_build_cookie_args_valid_cookie_file(tmp_path: Path) -> None:
    from worker.download_runner import build_cookie_args

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n")

    result = build_cookie_args(cookie_file=str(cookie_file))

    assert result == {"cookiefile": str(cookie_file)}


def test_build_cookie_args_invalid_file_path_warns(caplog) -> None:
    from worker.download_runner import build_cookie_args

    with caplog.at_level("WARNING"):
        result = build_cookie_args(cookie_file="/nonexistent/path/cookies.txt")

    assert result == {}
    assert "/nonexistent/path/cookies.txt" in caplog.text


def test_build_cookie_args_file_takes_precedence_over_browser(tmp_path: Path) -> None:
    from worker.download_runner import build_cookie_args

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n")

    result = build_cookie_args(browser_name="chrome", cookie_file=str(cookie_file))

    assert result == {"cookiefile": str(cookie_file)}
    assert "cookiesfrombrowser" not in result


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


def test_ai_pipeline_completed_saves_summary_and_mindmap(monkeypatch, session, tmp_path: Path) -> None:
    """Test that AI pipeline saves summary and mindmap when AI succeeds."""
    from app.core.config import get_settings
    from app.services.ai import AIService
    from app.services.transcription import TranscriptionService
    from worker.ai_pipeline import process_ai_pipeline
    from worker.domain import AIProcessStatus, DownloadArtifact

    monkeypatch.setenv("LLM_API_KEY", "fake_key")
    monkeypatch.setenv("TRANSCRIPTION_API_KEY", "fake_key")
    get_settings.cache_clear()

    user = _user(session)
    task = _task(session, user, TaskState.SUCCEEDED)
    artifact = DownloadArtifact(path=tmp_path / "video.mp4", filename="video.mp4", size_bytes=100)
    artifact.path.write_bytes(b"video")

    # Mock subprocess for ffmpeg
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    # Mock transcription service
    mock_transcript = "This is a test transcript"
    mock_summary = "Test summary with key points"
    mock_mindmap = "mindmap\n  root\n    Topic1\n    Topic2"

    class MockTranscriptionService:
        async def transcribe_audio(self, path: str) -> str:
            return mock_transcript

    class MockAIService:
        async def summarize_transcript(self, transcript: str) -> str:
            return mock_summary

        async def generate_mindmap(self, transcript: str) -> str:
            return mock_mindmap

    monkeypatch.setattr("app.services.transcription.TranscriptionService", MockTranscriptionService)
    monkeypatch.setattr("app.services.ai.AIService", MockAIService)

    result = process_ai_pipeline(session, task, artifact)

    assert result.status == AIProcessStatus.COMPLETED
    assert task.ai_status == AIProcessStatus.COMPLETED.value
    assert task.ai_summary == mock_summary
    assert task.ai_mindmap == mock_mindmap
    assert task.ai_error is None
    get_settings.cache_clear()


def test_ai_pipeline_failed_records_error_without_leaking_keys(monkeypatch, session, tmp_path: Path) -> None:
    """Test that AI pipeline records error without leaking API keys."""
    from app.core.config import get_settings
    from app.services.transcription import TranscriptionService
    from worker.ai_pipeline import process_ai_pipeline
    from worker.domain import AIProcessStatus, DownloadArtifact

    monkeypatch.setenv("LLM_API_KEY", "super_secret_api_key_12345")
    monkeypatch.setenv("TRANSCRIPTION_API_KEY", "super_secret_transcription_key_67890")
    get_settings.cache_clear()

    user = _user(session)
    task = _task(session, user, TaskState.SUCCEEDED)
    artifact = DownloadArtifact(path=tmp_path / "video.mp4", filename="video.mp4", size_bytes=100)
    artifact.path.write_bytes(b"video")

    # Mock subprocess for ffmpeg
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    # Mock transcription service to fail with error containing API key
    class MockTranscriptionService:
        async def transcribe_audio(self, path: str) -> None:
            raise RuntimeError("API call failed with key super_secret_api_key_12345")

    monkeypatch.setattr("app.services.transcription.TranscriptionService", MockTranscriptionService)

    result = process_ai_pipeline(session, task, artifact)

    assert result.status == AIProcessStatus.FAILED
    assert task.ai_status == AIProcessStatus.FAILED.value
    assert task.ai_error is not None
    # Verify API keys are not leaked in error messages
    assert "super_secret_api_key_12345" not in task.ai_error
    assert "super_secret_transcription_key_67890" not in task.ai_error
    get_settings.cache_clear()


def test_ai_pipeline_failed_records_readable_error(monkeypatch, session, tmp_path: Path) -> None:
    """Test that AI pipeline records readable error messages."""
    from app.core.config import get_settings
    from app.services.transcription import TranscriptionService
    from worker.ai_pipeline import process_ai_pipeline
    from worker.domain import AIProcessStatus, DownloadArtifact

    monkeypatch.setenv("LLM_API_KEY", "fake_key")
    monkeypatch.setenv("TRANSCRIPTION_API_KEY", "fake_key")
    get_settings.cache_clear()

    user = _user(session)
    task = _task(session, user, TaskState.SUCCEEDED)
    artifact = DownloadArtifact(path=tmp_path / "video.mp4", filename="video.mp4", size_bytes=100)
    artifact.path.write_bytes(b"video")

    # Mock subprocess for ffmpeg
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    # Mock transcription service to fail with generic error
    class MockTranscriptionService:
        async def transcribe_audio(self, path: str) -> None:
            raise RuntimeError("Transcription service unavailable")

    monkeypatch.setattr("app.services.transcription.TranscriptionService", MockTranscriptionService)

    result = process_ai_pipeline(session, task, artifact)

    assert result.status == AIProcessStatus.FAILED
    assert task.ai_status == AIProcessStatus.FAILED.value
    assert "Transcription service unavailable" in task.ai_error
    get_settings.cache_clear()
