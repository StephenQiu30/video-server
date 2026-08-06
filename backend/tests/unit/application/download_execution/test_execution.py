from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest
from app.application.download_execution import ExecutionDisposition
from app.domain.downloads import DownloadErrorCode
from app.infrastructure.media_runner_models import (
    MediaRunnerClientError,
    RunnerArtifact,
)
from tests.unit.application.download_execution.helpers import fixture


def artifact(tmp_path, data: bytes = b"controlled-video") -> RunnerArtifact:
    workspace = tmp_path / "task-workspace"
    workspace.mkdir(parents=True)
    path = workspace / "artifact.mp4"
    path.write_bytes(data)
    return RunnerArtifact(
        task_id="placeholder",
        workspace=workspace,
        artifact=path,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        duration_seconds=30.0,
        container="mp4",
        video_streams=1,
        audio_streams=1,
    )


@pytest.mark.asyncio
async def test_success_revalidates_identity_uploads_and_completes(tmp_path) -> None:
    case = fixture(artifact(tmp_path))
    case.runner.delay = 0.004

    result = await case.execution.execute(case.job_id)

    assert result is ExecutionDisposition.ACK
    assert case.runner.download_arguments[3] == {
        "expected_provider_media_id": "video-1",
        "expected_extractor_key": "Controlled",
    }
    assert case.storage.uploads[0][0] == (f"downloads/{case.job_id}/1/video.mp4")
    assert case.repository.success.sha256 == case.runner.artifact.sha256
    stages = [item[0] for item in case.repository.heartbeats]
    assert "downloading" in stages
    assert stages[-2:] == ["verifying", "uploading"]
    assert [item[1] for item in case.repository.heartbeats] == sorted(
        item[1] for item in case.repository.heartbeats
    )
    assert case.cleaner.calls[0][1] == case.runner.artifact.workspace


@pytest.mark.asyncio
async def test_runner_and_storage_failures_converge_before_ack(tmp_path) -> None:
    runner_case = fixture(artifact(tmp_path / "runner"))
    runner_case.runner.error = MediaRunnerClientError("download_timeout", 504)
    assert await runner_case.execution.execute(runner_case.job_id) is (
        ExecutionDisposition.ACK
    )
    assert runner_case.repository.failure["error_code"] == (
        DownloadErrorCode.DOWNLOAD_TIMEOUT.value
    )
    assert runner_case.repository.failure["retryable"] is True
    assert runner_case.cleaner.calls

    storage_case = fixture(artifact(tmp_path / "storage"))
    storage_case.storage.error = OSError("minio unavailable")
    assert await storage_case.execution.execute(storage_case.job_id) is (
        ExecutionDisposition.ACK
    )
    assert storage_case.repository.failure["error_code"] == (
        DownloadErrorCode.STORAGE_UNAVAILABLE.value
    )
    assert storage_case.repository.failure["retryable"] is True
    assert storage_case.cleaner.calls


@pytest.mark.asyncio
async def test_duplicate_and_hash_mismatch_are_idempotent(tmp_path) -> None:
    duplicate = fixture(artifact(tmp_path / "duplicate"))
    duplicate.repository.claimed = False
    duplicate.repository.status = "succeeded"
    assert await duplicate.execution.execute(duplicate.job_id) is (
        ExecutionDisposition.ACK
    )
    assert duplicate.runner.download_arguments is None

    mismatch_artifact = artifact(tmp_path / "mismatch")
    mismatch_artifact = replace(mismatch_artifact, sha256="0" * 64)
    mismatch = fixture(mismatch_artifact)
    assert await mismatch.execution.execute(mismatch.job_id) is (
        ExecutionDisposition.ACK
    )
    assert mismatch.repository.failure["error_code"] == (
        DownloadErrorCode.MEDIA_VALIDATION_FAILED.value
    )
    assert mismatch.storage.uploads == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("cancelled", ExecutionDisposition.ACK),
        ("queued", ExecutionDisposition.REQUEUE),
    ],
)
async def test_cancel_or_lease_loss_cancels_runner(tmp_path, status, expected) -> None:
    case = fixture(artifact(tmp_path / status))
    case.runner.block = True
    case.repository.heartbeat_results = [False]
    case.repository.status = status

    assert await case.execution.execute(case.job_id) is expected
    assert case.runner.cancelled == 1
    assert case.cleaner.calls
