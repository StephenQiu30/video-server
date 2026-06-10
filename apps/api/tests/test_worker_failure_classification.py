"""Tests for Worker failure classification, retryability, and happy-path integration.

PLAN05 验收：
- Worker 成功推进状态并完成主视频下载
- 常见失败返回稳定错误码
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.models import DownloadTask, User
from video_downloader_shared.states import TaskState
from worker.domain import FailureInfo, WorkerFailureCode, WorkerStage
from worker.failures import JobFailure, failure_code, failure_info_from_exception, format_failure_reason


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(session) -> User:
    user = User(
        email="failure-classification@example.com",
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


# ---------------------------------------------------------------------------
# 1. failure_code() full classification coverage
# ---------------------------------------------------------------------------


class TestFailureCodeClassification:
    """Verify failure_code() maps all known exception patterns to the correct WorkerFailureCode."""

    def test_download_failed_is_fallback_for_unknown_errors(self) -> None:
        """Unknown exceptions fall through to DOWNLOAD_FAILED."""
        assert failure_code(RuntimeError("something completely unexpected")) == WorkerFailureCode.DOWNLOAD_FAILED

    def test_platform_restricted_login_required(self) -> None:
        """Login-required errors are classified as PLATFORM_RESTRICTED."""
        assert failure_code(RuntimeError("ERROR: login required")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_sign_in(self) -> None:
        assert failure_code(RuntimeError("ERROR: sign in to watch")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_members_only(self) -> None:
        assert failure_code(RuntimeError("ERROR: members-only content")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_premium(self) -> None:
        assert failure_code(RuntimeError("ERROR: premium content")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_drm(self) -> None:
        assert failure_code(RuntimeError("ERROR: drm protected")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_geo_restricted(self) -> None:
        assert failure_code(RuntimeError("ERROR: geo restricted content")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_region(self) -> None:
        assert failure_code(RuntimeError("ERROR: not available in your region")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_restricted_chinese_markers(self) -> None:
        """Chinese restriction markers are recognized."""
        assert failure_code(RuntimeError("该内容仅限会员观看")) == WorkerFailureCode.PLATFORM_RESTRICTED
        assert failure_code(RuntimeError("需要付费才能访问")) == WorkerFailureCode.PLATFORM_RESTRICTED

    def test_platform_rate_limited_429(self) -> None:
        """HTTP 429 errors are classified as PLATFORM_RATE_LIMITED."""
        assert failure_code(RuntimeError("ERROR: HTTP Error 429: Too Many Requests")) == WorkerFailureCode.PLATFORM_RATE_LIMITED

    def test_platform_rate_limited_captcha(self) -> None:
        assert failure_code(RuntimeError("ERROR: captcha required")) == WorkerFailureCode.PLATFORM_RATE_LIMITED

    def test_platform_rate_limited_too_many_requests(self) -> None:
        assert failure_code(RuntimeError("ERROR: too many requests, slow down")) == WorkerFailureCode.PLATFORM_RATE_LIMITED

    def test_platform_rate_limited_rate_limit(self) -> None:
        assert failure_code(RuntimeError("ERROR: rate limit exceeded")) == WorkerFailureCode.PLATFORM_RATE_LIMITED

    def test_platform_rate_limited_chinese_markers(self) -> None:
        """Chinese rate-limit markers are recognized."""
        assert failure_code(RuntimeError("访问过于频繁，请稍后再试")) == WorkerFailureCode.PLATFORM_RATE_LIMITED
        assert failure_code(RuntimeError("请完成验证码")) == WorkerFailureCode.PLATFORM_RATE_LIMITED

    def test_ffprobe_failed_classified(self) -> None:
        """FFprobe validation failures are classified as FFPROBE_FAILED."""
        assert failure_code(JobFailure("ffprobe_failed", "FFmpeg / ffprobe 无法校验输出文件")) == WorkerFailureCode.FFPROBE_FAILED

    def test_media_tools_missing_classified(self) -> None:
        assert failure_code(JobFailure("media_tools_missing", "缺少媒体工具")) == WorkerFailureCode.MEDIA_TOOLS_MISSING

    def test_storage_failed_classified(self) -> None:
        assert failure_code(JobFailure("storage_failed", "上传失败")) == WorkerFailureCode.STORAGE_FAILED

    def test_task_canceled_classified(self) -> None:
        assert failure_code(JobFailure("task_canceled", "任务已取消")) == WorkerFailureCode.TASK_CANCELED

    def test_existing_classifications_still_work(self) -> None:
        """Verify all existing classifications are preserved."""
        assert failure_code(RuntimeError("ERROR: requested format is not available")) == WorkerFailureCode.FORMAT_UNAVAILABLE
        assert failure_code(RuntimeError("ERROR: file is larger than max-filesize")) == WorkerFailureCode.FILE_TOO_LARGE
        assert failure_code(RuntimeError("ERROR: job timed out")) == WorkerFailureCode.TASK_TIMEOUT
        assert failure_code(RuntimeError("ERROR: unsupported url")) == WorkerFailureCode.UNSUPPORTED_PLATFORM


# ---------------------------------------------------------------------------
# 2. Retryability matrix
# ---------------------------------------------------------------------------


class TestRetryabilityMatrix:
    """Verify failure_info_from_exception sets retryable correctly for each failure code."""

    def _info(self, exc: Exception, stage: WorkerStage = WorkerStage.DOWNLOAD) -> FailureInfo:
        return failure_info_from_exception(exc, stage)

    def test_download_failed_is_retryable(self) -> None:
        info = self._info(RuntimeError("network error"))
        assert info.code == WorkerFailureCode.DOWNLOAD_FAILED
        assert info.retryable is True

    def test_storage_failed_is_retryable(self) -> None:
        info = self._info(JobFailure("storage_failed", "upload failed"), WorkerStage.UPLOAD)
        assert info.code == WorkerFailureCode.STORAGE_FAILED
        assert info.retryable is True

    def test_task_timeout_is_retryable(self) -> None:
        info = self._info(RuntimeError("job timed out"))
        assert info.code == WorkerFailureCode.TASK_TIMEOUT
        assert info.retryable is True

    def test_platform_rate_limited_is_retryable(self) -> None:
        info = self._info(RuntimeError("ERROR: 429 too many requests"))
        assert info.code == WorkerFailureCode.PLATFORM_RATE_LIMITED
        assert info.retryable is True

    def test_format_unavailable_is_not_retryable(self) -> None:
        info = self._info(RuntimeError("ERROR: requested format is not available"))
        assert info.code == WorkerFailureCode.FORMAT_UNAVAILABLE
        assert info.retryable is False

    def test_file_too_large_is_not_retryable(self) -> None:
        info = self._info(RuntimeError("ERROR: file is larger than max-filesize"))
        assert info.code == WorkerFailureCode.FILE_TOO_LARGE
        assert info.retryable is False

    def test_unsupported_platform_is_not_retryable(self) -> None:
        info = self._info(RuntimeError("ERROR: unsupported url"))
        assert info.code == WorkerFailureCode.UNSUPPORTED_PLATFORM
        assert info.retryable is False

    def test_browser_cookies_unavailable_is_not_retryable(self) -> None:
        info = self._info(RuntimeError("failed to decrypt Chrome cookies"))
        assert info.code == WorkerFailureCode.BROWSER_COOKIES_UNAVAILABLE
        assert info.retryable is False

    def test_platform_restricted_is_not_retryable(self) -> None:
        info = self._info(RuntimeError("ERROR: login required"))
        assert info.code == WorkerFailureCode.PLATFORM_RESTRICTED
        assert info.retryable is False

    def test_media_tools_missing_is_not_retryable(self) -> None:
        info = self._info(JobFailure("media_tools_missing", "缺少媒体工具"))
        assert info.code == WorkerFailureCode.MEDIA_TOOLS_MISSING
        assert info.retryable is False

    def test_ffprobe_failed_is_not_retryable(self) -> None:
        info = self._info(JobFailure("ffprobe_failed", "ffprobe 校验失败"))
        assert info.code == WorkerFailureCode.FFPROBE_FAILED
        assert info.retryable is False

    def test_task_canceled_is_not_retryable(self) -> None:
        info = self._info(JobFailure("task_canceled", "任务已取消"))
        assert info.code == WorkerFailureCode.TASK_CANCELED
        assert info.retryable is False


# ---------------------------------------------------------------------------
# 3. Stage tracking in failure_info_from_exception
# ---------------------------------------------------------------------------


class TestStageTracking:
    """Verify failure_info_from_exception preserves the stage where failure occurred."""

    def test_download_stage_preserved(self) -> None:
        info = failure_info_from_exception(RuntimeError("network error"), WorkerStage.DOWNLOAD)
        assert info.stage == WorkerStage.DOWNLOAD

    def test_upload_stage_preserved(self) -> None:
        info = failure_info_from_exception(JobFailure("storage_failed", "upload failed"), WorkerStage.UPLOAD)
        assert info.stage == WorkerStage.UPLOAD

    def test_probe_stage_preserved(self) -> None:
        info = failure_info_from_exception(JobFailure("ffprobe_failed", "probe failed"), WorkerStage.PROBE)
        assert info.stage == WorkerStage.PROBE

    def test_start_stage_preserved(self) -> None:
        info = failure_info_from_exception(JobFailure("media_tools_missing", "no ffmpeg"), WorkerStage.START)
        assert info.stage == WorkerStage.START


# ---------------------------------------------------------------------------
# 4. _mark_failed stage propagation
# ---------------------------------------------------------------------------


class TestMarkFailedStagePropagation:
    """Verify _mark_failed writes the correct failure stage to the task.

    _mark_failed is called by process_download_task's exception handler.
    We test it directly via the _mark_failed function to avoid session isolation issues.
    """

    def test_mark_failed_records_failure_code_for_download_error(self, session) -> None:
        """Download errors produce a failure_code on the task."""
        from worker.jobs import _mark_failed

        user = _user(session)
        task = _task(session, user, TaskState.RUNNING)

        _mark_failed(session, task.id, RuntimeError("ERROR: network timeout"))

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.FAILED.value
        assert task.failure_code == WorkerFailureCode.TASK_TIMEOUT.value
        assert task.failure_reason is not None

    def test_mark_failed_records_failure_code_for_upload_error(self, session) -> None:
        """Upload errors produce a failure_code on the task."""
        from worker.jobs import _mark_failed

        user = _user(session)
        task = _task(session, user, TaskState.RUNNING)

        _mark_failed(session, task.id, JobFailure("storage_failed", "文件上传对象存储失败"))

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.FAILED.value
        assert task.failure_code == WorkerFailureCode.STORAGE_FAILED.value

    def test_mark_failed_records_failure_code_for_platform_restricted(self, session) -> None:
        """Platform-restricted errors produce platform_restricted failure_code."""
        from worker.jobs import _mark_failed

        user = _user(session)
        task = _task(session, user, TaskState.RUNNING)

        _mark_failed(session, task.id, RuntimeError("ERROR: login required"))

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.FAILED.value
        assert task.failure_code == WorkerFailureCode.PLATFORM_RESTRICTED.value

    def test_mark_failed_records_failure_code_for_rate_limited(self, session) -> None:
        """Rate-limited errors produce platform_rate_limited failure_code."""
        from worker.jobs import _mark_failed

        user = _user(session)
        task = _task(session, user, TaskState.RUNNING)

        _mark_failed(session, task.id, RuntimeError("ERROR: 429 Too Many Requests"))

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.FAILED.value
        assert task.failure_code == WorkerFailureCode.PLATFORM_RATE_LIMITED.value

    def test_mark_failed_skips_already_canceled_task(self, session) -> None:
        """_mark_failed should not overwrite a canceled task."""
        from worker.jobs import _mark_failed

        user = _user(session)
        task = _task(session, user, TaskState.CANCELED)

        _mark_failed(session, task.id, RuntimeError("some error"))

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.CANCELED.value


# ---------------------------------------------------------------------------
# 5. process_download_task happy path (integration)
# ---------------------------------------------------------------------------


class TestProcessDownloadTaskHappyPath:
    """Verify the full Worker download lifecycle: queued -> running -> succeeded."""

    def _session_factory(self, session):
        """Create a SessionLocal replacement that returns a no-close wrapper."""

        class _NoClose:
            """Wrap session to prevent process_download_task from closing the test session."""
            def __getattr__(self, name):
                if name == "close":
                    return lambda: None
                return getattr(session, name)

        class SessionFactory:
            def __call__(self_inner):
                return _NoClose()

        return SessionFactory()

    def test_successful_download_transitions_to_succeeded(
        self, monkeypatch, session, tmp_path
    ) -> None:
        """Full happy path: download, probe, upload, mark succeeded."""
        from datetime import timedelta

        from worker import jobs
        from worker.domain import DownloadArtifact, StoredArtifact

        user = _user(session)
        task = _task(session, user, TaskState.QUEUED)

        fake_video = tmp_path / "video.mp4"
        fake_video.write_bytes(b"fake video content")
        artifact = DownloadArtifact(
            path=fake_video, filename="video.mp4", size_bytes=fake_video.stat().st_size
        )
        stored = StoredArtifact(
            object_key=f"users/{user.id}/tasks/{task.id}/video.mp4",
            object_size=fake_video.stat().st_size,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        monkeypatch.setattr(jobs, "SessionLocal", self._session_factory(session))
        monkeypatch.setattr(jobs, "download_task_artifact", lambda *_: (artifact, {"title": "test"}))
        monkeypatch.setattr(jobs, "assert_media_tools_available", lambda: None)
        monkeypatch.setattr(jobs, "assert_artifact_size", lambda *_: None)
        monkeypatch.setattr(jobs, "probe_with_ffprobe", lambda *_: None)
        monkeypatch.setattr(jobs, "upload_artifact", lambda *_: stored)
        monkeypatch.setattr(jobs, "process_ai_pipeline", lambda *_: None)
        monkeypatch.setattr(jobs, "_collect_and_store_enhanced", lambda *_: None)

        jobs.process_download_task(task.id)

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.SUCCEEDED.value
        assert task.progress == 100
        assert task.output_filename == "video.mp4"
        assert task.object_key == stored.object_key

    def test_successful_download_records_succeeded_event(
        self, monkeypatch, session, tmp_path
    ) -> None:
        """Happy path should record task events for state transitions."""
        from datetime import timedelta

        from worker import jobs
        from worker.domain import DownloadArtifact, StoredArtifact

        user = _user(session)
        task = _task(session, user, TaskState.QUEUED)

        fake_video = tmp_path / "video.mp4"
        fake_video.write_bytes(b"fake video content")
        artifact = DownloadArtifact(
            path=fake_video, filename="video.mp4", size_bytes=fake_video.stat().st_size
        )
        stored = StoredArtifact(
            object_key=f"users/{user.id}/tasks/{task.id}/video.mp4",
            object_size=fake_video.stat().st_size,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        monkeypatch.setattr(jobs, "SessionLocal", self._session_factory(session))
        monkeypatch.setattr(jobs, "download_task_artifact", lambda *_: (artifact, {"title": "test"}))
        monkeypatch.setattr(jobs, "assert_media_tools_available", lambda: None)
        monkeypatch.setattr(jobs, "assert_artifact_size", lambda *_: None)
        monkeypatch.setattr(jobs, "probe_with_ffprobe", lambda *_: None)
        monkeypatch.setattr(jobs, "upload_artifact", lambda *_: stored)
        monkeypatch.setattr(jobs, "process_ai_pipeline", lambda *_: None)
        monkeypatch.setattr(jobs, "_collect_and_store_enhanced", lambda *_: None)

        jobs.process_download_task(task.id)

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.SUCCEEDED.value
        # Verify task events were recorded
        from app.models import TaskEvent
        events = session.query(TaskEvent).filter(TaskEvent.task_id == task.id).all()
        state_messages = [e.message for e in events]
        assert any("Worker 已开始下载" in m for m in state_messages)
        assert any("文件已保存到私有对象存储" in m for m in state_messages)

    def test_download_failure_marks_failed_with_correct_code(
        self, monkeypatch, session
    ) -> None:
        """Download failure should mark task as FAILED with correct failure_code."""
        from worker import jobs

        user = _user(session)
        task = _task(session, user, TaskState.QUEUED)

        monkeypatch.setattr(jobs, "SessionLocal", self._session_factory(session))
        monkeypatch.setattr(jobs, "assert_media_tools_available", lambda: None)
        monkeypatch.setattr(
            jobs,
            "download_task_artifact",
            lambda *_: (_ for _ in ()).throw(RuntimeError("ERROR: login required")),
        )

        try:
            jobs.process_download_task(task.id)
        except RuntimeError:
            pass

        session.expire_all()
        task = session.get(DownloadTask, task.id)
        assert task.state == TaskState.FAILED.value
        assert task.failure_code is not None
        assert task.failure_reason is not None
