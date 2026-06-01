from pathlib import Path
import os

from worker import jobs
from worker.domain import DownloadArtifact, WorkerFailureCode
from worker.failures import failure_info_from_exception
from worker.jobs import (
    JobFailure,
    _apply_browser_cookie_options,
    _apply_download_resilience_options,
    _assert_media_tools_available,
    _cleanup_task_work_dir,
    _failure_code,
    _format_failure_reason,
    _raise_task_canceled,
    _resolve_output_path,
)
from worker.media_probe import assert_artifact_size


def test_resolve_output_path_uses_prepared_file(tmp_path: Path) -> None:
    prepared = tmp_path / "video.webm"
    prepared.write_text("video")

    assert _resolve_output_path(tmp_path, prepared) == prepared


def test_resolve_output_path_falls_back_to_latest_file(tmp_path: Path) -> None:
    old_file = tmp_path / "video.f137.mp4"
    latest_file = tmp_path / "video.mp4"
    old_file.write_text("old")
    latest_file.write_text("latest")
    os.utime(old_file, (1, 1))
    os.utime(latest_file, (2, 2))

    assert _resolve_output_path(tmp_path, tmp_path / "missing.webm") == latest_file


def test_cleanup_task_work_dir_removes_temporary_download_outputs(tmp_path: Path) -> None:
    task_dir = tmp_path / "user-1" / "task-1"
    task_dir.mkdir(parents=True)
    (task_dir / "video.mp4").write_text("temporary output")

    _cleanup_task_work_dir(task_dir)

    assert not task_dir.exists()


def test_format_failure_reason_trims_and_redacts_sensitive_url() -> None:
    reason = _format_failure_reason(
        RuntimeError("ERROR: failed https://example.com/video?token=secret\nsecond line")
    )

    assert reason.startswith("failed https://example.com/video")
    assert "secret" not in reason
    assert "second line" not in reason


def test_media_tools_check_requires_ffmpeg_and_ffprobe(monkeypatch) -> None:
    monkeypatch.setattr(jobs.shutil, "which", lambda _: None)

    try:
        _assert_media_tools_available()
    except RuntimeError as exc:
        assert "ffmpeg" in str(exc)
        assert "ffprobe" in str(exc)
    else:
        raise AssertionError("expected media tools check to fail")


def test_media_tools_check_passes_when_tools_exist(monkeypatch) -> None:
    monkeypatch.setattr(jobs.shutil, "which", lambda name: f"/opt/homebrew/bin/{name}")

    _assert_media_tools_available()


def test_failure_code_uses_job_failure_code() -> None:
    assert _failure_code(JobFailure("storage_failed", "upload failed")) == "storage_failed"


def test_failure_code_classifies_timeout_message() -> None:
    assert _failure_code(RuntimeError("job timed out")) == "task_timeout"


def test_failure_code_classifies_unavailable_format() -> None:
    exc = RuntimeError("ERROR: requested format is not available")

    assert _failure_code(exc) == "format_unavailable"
    assert "未提供所选清晰度" in _format_failure_reason(exc)


def test_download_resilience_options_are_bounded() -> None:
    options: dict = {}

    _apply_download_resilience_options(options)

    assert options["retries"] == 3
    assert options["fragment_retries"] == 3
    assert options["file_access_retries"] == 3
    assert options["continuedl"] is True


def test_task_canceled_failure_is_preserved() -> None:
    try:
        _raise_task_canceled()
    except JobFailure as exc:
        assert exc.code == "task_canceled"
        assert _format_failure_reason(exc) == "任务已取消"
    else:
        raise AssertionError("expected cancellation failure")


def test_apply_browser_cookie_options_uses_tuple_form() -> None:
    options: dict = {}

    _apply_browser_cookie_options(options, "chrome")

    assert options["cookiesfrombrowser"] == ("chrome",)


def test_apply_browser_cookie_options_can_be_disabled() -> None:
    options: dict = {}

    _apply_browser_cookie_options(options, "none")

    assert "cookiesfrombrowser" not in options


def test_browser_cookie_failure_is_diagnostic_and_redacted() -> None:
    exc = RuntimeError("failed to decrypt Chrome cookies at /Users/example/Cookies")

    assert _failure_code(exc) == "browser_cookies_unavailable"
    reason = _format_failure_reason(exc)
    assert "无法读取本机 Chrome 登录态" in reason
    assert "/Users/example/Cookies" not in reason


def test_failure_info_has_code_and_reason_for_media_tools_missing() -> None:
    exc = JobFailure("media_tools_missing", "当前环境缺少媒体工具：ffmpeg, ffprobe")

    info = failure_info_from_exception(exc, __import__("worker.domain", fromlist=["WorkerStage"]).WorkerStage.DOWNLOAD)

    assert info.code == WorkerFailureCode.MEDIA_TOOLS_MISSING
    assert "媒体工具" in info.reason
    assert info.retryable is False


def test_failure_info_has_code_and_reason_for_file_too_large() -> None:
    exc = JobFailure("file_too_large", "文件超过限制：9999999999 > 2147483648")

    info = failure_info_from_exception(exc, __import__("worker.domain", fromlist=["WorkerStage"]).WorkerStage.DOWNLOAD)

    assert info.code == WorkerFailureCode.FILE_TOO_LARGE
    assert "文件超过限制" in info.reason
    assert info.retryable is False


def test_failure_info_has_code_and_reason_for_storage_failed() -> None:
    exc = JobFailure("storage_failed", "文件上传对象存储失败")

    info = failure_info_from_exception(exc, __import__("worker.domain", fromlist=["WorkerStage"]).WorkerStage.UPLOAD)

    assert info.code == WorkerFailureCode.STORAGE_FAILED
    assert "对象存储" in info.reason
    assert info.retryable is True


def test_assert_artifact_size_raises_for_oversized_file(monkeypatch) -> None:
    import types

    class FakeSettings:
        max_file_size_bytes = 100

    class FakeUser:
        max_file_size_bytes = 100

    class FakeTask:
        user = FakeUser()

    monkeypatch.setattr("worker.media_probe.get_settings", lambda: FakeSettings())

    artifact = DownloadArtifact(path=Path("/tmp/fake.mp4"), filename="fake.mp4", size_bytes=999)

    try:
        assert_artifact_size(artifact, FakeTask())
    except JobFailure as exc:
        assert exc.code == "file_too_large"
        assert _format_failure_reason(exc) == "文件超过限制：999 > 100"
    else:
        raise AssertionError("expected file_too_large failure")
