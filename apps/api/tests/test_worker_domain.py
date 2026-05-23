from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from worker.domain import (
    AIProcessResult,
    AIProcessStatus,
    DownloadArtifact,
    FailureInfo,
    StoredArtifact,
    WorkerContext,
    WorkerFailureCode,
    WorkerStage,
)


def test_worker_domain_enums_have_stable_values() -> None:
    assert WorkerStage.DOWNLOAD == "download"
    assert WorkerStage.PROBE == "probe"
    assert WorkerStage.UPLOAD == "upload"
    assert WorkerStage.AI == "ai"
    assert WorkerFailureCode.MEDIA_TOOLS_MISSING == "media_tools_missing"
    assert WorkerFailureCode.BROWSER_COOKIES_UNAVAILABLE == "browser_cookies_unavailable"
    assert AIProcessStatus.SKIPPED == "skipped"
    assert AIProcessStatus.COMPLETED == "completed"


def test_worker_context_is_immutable() -> None:
    context = WorkerContext(
        task_id="task-1",
        user_id=7,
        source_url="https://example.com/video",
        format_id="best",
        title="Video",
        work_dir=Path("/tmp/work"),
        max_file_size_bytes=1024,
        file_retention_hours=24,
    )

    with pytest.raises(FrozenInstanceError):
        context.title = "changed"  # type: ignore[misc]


def test_worker_artifact_dtos_define_internal_boundaries() -> None:
    download = DownloadArtifact(path=Path("/tmp/video.mp4"), filename="video.mp4", size_bytes=128)
    stored = StoredArtifact(
        object_key="users/7/tasks/task-1/video.mp4",
        object_size=128,
        expires_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    failure = FailureInfo(
        code=WorkerFailureCode.STORAGE_FAILED,
        reason="upload failed",
        stage=WorkerStage.UPLOAD,
        retryable=True,
    )
    ai = AIProcessResult(status=AIProcessStatus.SKIPPED)

    assert download.content_type == "application/octet-stream"
    assert stored.object_size == download.size_bytes
    assert failure.code == WorkerFailureCode.STORAGE_FAILED
    assert ai.summary is None
