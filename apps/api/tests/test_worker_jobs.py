from pathlib import Path
import os

from worker import jobs
from worker.jobs import (
    JobFailure,
    _assert_media_tools_available,
    _cleanup_task_work_dir,
    _failure_code,
    _format_failure_reason,
    _resolve_output_path,
)


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
