from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.downloads import (
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DownloadErrorCode,
    DownloadJob,
    DownloadPlan,
    DownloadStage,
    DownloadStatus,
    DynamicRange,
    FpsBucket,
    InvalidJobTransition,
    VideoCodecFamily,
)

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)


def plan() -> DownloadPlan:
    return DownloadPlan(
        height=1080,
        width=1920,
        fps_bucket=FpsBucket.FPS_30,
        dynamic_range=DynamicRange.SDR,
        video_codec_family=VideoCodecFamily.H264,
        audio_codec_family=AudioCodecFamily.AAC,
        audio_language=None,
        container_preference=ContainerPreference.MP4,
        compatibility_profile=CompatibilityProfile.BALANCED,
    )


def claimed_job() -> DownloadJob:
    job = DownloadJob.create("job-1", plan())
    job.claim("worker-a", NOW, timedelta(seconds=30))
    return job


def test_claim_sets_initial_lease_and_increments_attempt() -> None:
    job = claimed_job()

    assert job.status is DownloadStatus.RUNNING
    assert job.stage is DownloadStage.REVALIDATING
    assert job.attempt == 1
    assert job.lease_owner == "worker-a"
    assert job.lease_expires_at == NOW + timedelta(seconds=30)
    assert job.heartbeat_at == NOW
    assert job.started_at == NOW


def test_only_linear_running_stage_transitions_are_allowed() -> None:
    job = claimed_job()

    with pytest.raises(InvalidJobTransition):
        job.advance("worker-a", DownloadStage.REMUXING, progress=30, now=NOW)

    for stage, progress in [
        (DownloadStage.REVALIDATING, 5),
        (DownloadStage.DOWNLOADING, 20),
        (DownloadStage.REMUXING, 70),
        (DownloadStage.VERIFYING, 85),
        (DownloadStage.UPLOADING, 95),
    ]:
        job.advance("worker-a", stage, progress=progress, now=NOW)

    job.succeed("worker-a", NOW + timedelta(seconds=1))
    assert job.status is DownloadStatus.SUCCEEDED
    assert job.stage is None
    assert job.progress == 100
    assert job.finished_at == NOW + timedelta(seconds=1)
    assert job.lease_owner is None


def test_progress_is_monotonic_and_bounded() -> None:
    job = claimed_job()
    job.advance("worker-a", DownloadStage.REVALIDATING, 10, NOW)

    with pytest.raises(InvalidJobTransition):
        job.advance("worker-a", DownloadStage.REVALIDATING, 9, NOW)
    with pytest.raises(InvalidJobTransition):
        job.advance("worker-a", DownloadStage.REVALIDATING, 101, NOW)


def test_stale_or_expired_worker_cannot_mutate_job() -> None:
    job = claimed_job()

    with pytest.raises(InvalidJobTransition):
        job.heartbeat("worker-b", NOW, timedelta(seconds=30))
    with pytest.raises(InvalidJobTransition):
        job.advance(
            "worker-a",
            DownloadStage.REVALIDATING,
            1,
            NOW + timedelta(seconds=30),
        )


def test_heartbeat_extends_lease_without_changing_progress() -> None:
    job = claimed_job()
    heartbeat_at = NOW + timedelta(seconds=10)

    job.heartbeat("worker-a", heartbeat_at, timedelta(seconds=30))

    assert job.heartbeat_at == heartbeat_at
    assert job.lease_expires_at == heartbeat_at + timedelta(seconds=30)
    assert job.progress == 0


def test_retry_requeues_and_next_claim_increments_attempt() -> None:
    job = claimed_job()
    retry_at = NOW + timedelta(minutes=1)
    job.schedule_retry(
        "worker-a",
        DownloadErrorCode.STORAGE_UNAVAILABLE,
        now=NOW,
        retry_at=retry_at,
    )

    assert job.status is DownloadStatus.RETRY_WAIT
    assert job.error_code is DownloadErrorCode.STORAGE_UNAVAILABLE
    with pytest.raises(InvalidJobTransition):
        job.release_retry(retry_at - timedelta(microseconds=1))

    job.release_retry(retry_at)
    job.claim("worker-b", retry_at, timedelta(seconds=30))
    assert job.status is DownloadStatus.RUNNING
    assert job.attempt == 2
    assert job.lease_owner == "worker-b"
    assert job.error_code is None


def test_non_retryable_error_cannot_enter_retry_wait() -> None:
    job = claimed_job()

    with pytest.raises(InvalidJobTransition):
        job.schedule_retry(
            "worker-a",
            DownloadErrorCode.FORMAT_UNAVAILABLE,
            now=NOW,
            retry_at=NOW + timedelta(seconds=1),
        )


def test_expired_lease_retries_then_fails_at_attempt_limit() -> None:
    retrying = claimed_job()
    retry_at = NOW + timedelta(minutes=2)
    retrying.recover_expired_lease(
        NOW + timedelta(seconds=31), retry_at=retry_at, max_attempts=2
    )
    assert retrying.status is DownloadStatus.RETRY_WAIT
    assert retrying.error_code is DownloadErrorCode.WORKER_LOST

    exhausted = claimed_job()
    exhausted.recover_expired_lease(
        NOW + timedelta(seconds=31), retry_at=retry_at, max_attempts=1
    )
    assert exhausted.status is DownloadStatus.FAILED
    assert exhausted.error_code is DownloadErrorCode.WORKER_LOST


@pytest.mark.parametrize("status", [DownloadStatus.QUEUED, DownloadStatus.RETRY_WAIT])
def test_user_can_cancel_non_terminal_job(status: DownloadStatus) -> None:
    job = DownloadJob.create("job-1", plan())
    if status is DownloadStatus.RETRY_WAIT:
        job.claim("worker-a", NOW, timedelta(seconds=30))
        job.schedule_retry(
            "worker-a",
            DownloadErrorCode.WORKER_LOST,
            NOW,
            NOW + timedelta(seconds=1),
        )

    job.cancel(NOW)

    assert job.status is DownloadStatus.CANCELLED
    assert job.error_code is DownloadErrorCode.CANCELLED
    assert job.finished_at == NOW


def test_terminal_job_rejects_further_transitions() -> None:
    job = DownloadJob.create("job-1", plan())
    job.cancel(NOW)

    with pytest.raises(InvalidJobTransition):
        job.claim("worker-a", NOW, timedelta(seconds=30))
