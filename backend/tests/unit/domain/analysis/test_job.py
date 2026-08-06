from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.analysis import (
    AnalysisErrorCode,
    AnalysisJob,
    AnalysisStage,
    AnalysisStatus,
    InvalidAnalysisTransition,
)

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)
SHA256 = "a" * 64


def job() -> AnalysisJob:
    return AnalysisJob.create(
        job_id="analysis-1",
        artifact_id="artifact-1",
        input_sha256=SHA256,
        profile="standard-v1",
        schema_version="analysis.v1",
        output_language="zh-CN",
    )


def claimed() -> AnalysisJob:
    value = job()
    value.claim("worker-a", NOW, timedelta(seconds=30))
    return value


def test_claim_sets_lease_attempt_stage_and_version() -> None:
    value = claimed()

    assert value.status is AnalysisStatus.RUNNING
    assert value.stage is AnalysisStage.PREPARING
    assert value.attempt == 1
    assert value.version == 1
    assert value.lease_owner == "worker-a"
    assert value.lease_expires_at == NOW + timedelta(seconds=30)
    assert value.heartbeat_at == NOW


def test_stages_are_linear_and_success_requires_validation() -> None:
    value = claimed()

    with pytest.raises(InvalidAnalysisTransition):
        value.advance("worker-a", AnalysisStage.ANALYZING, 30, NOW)

    for stage, progress in (
        (AnalysisStage.PREPARING, 5),
        (AnalysisStage.TRANSCRIBING, 35),
        (AnalysisStage.ANALYZING, 70),
        (AnalysisStage.VALIDATING, 90),
    ):
        value.advance("worker-a", stage, progress, NOW)

    value.succeed("worker-a", NOW + timedelta(seconds=1))
    assert value.status is AnalysisStatus.SUCCEEDED
    assert value.progress == 100
    assert value.stage is None
    assert value.lease_owner is None


def test_lease_owner_expiry_and_progress_are_enforced() -> None:
    value = claimed()
    value.advance("worker-a", AnalysisStage.PREPARING, 10, NOW)

    with pytest.raises(InvalidAnalysisTransition):
        value.heartbeat("worker-b", NOW, timedelta(seconds=30))
    with pytest.raises(InvalidAnalysisTransition):
        value.advance("worker-a", AnalysisStage.PREPARING, 9, NOW)
    with pytest.raises(InvalidAnalysisTransition):
        value.advance(
            "worker-a",
            AnalysisStage.PREPARING,
            11,
            NOW + timedelta(seconds=30),
        )


def test_retry_requeues_and_increments_attempt_on_next_claim() -> None:
    value = claimed()
    retry_at = NOW + timedelta(minutes=1)
    value.schedule_retry(
        "worker-a",
        AnalysisErrorCode.PROVIDER_RATE_LIMITED,
        NOW,
        retry_at,
    )

    assert value.status is AnalysisStatus.RETRY_WAIT
    assert value.lease_owner is None
    with pytest.raises(InvalidAnalysisTransition):
        value.release_retry(retry_at - timedelta(microseconds=1))

    value.release_retry(retry_at)
    value.claim("worker-b", retry_at, timedelta(seconds=30))
    assert value.attempt == 2
    assert value.error_code is None


def test_expired_lease_retries_then_fails_at_attempt_limit() -> None:
    retrying = claimed()
    retrying.recover_expired_lease(
        NOW + timedelta(seconds=31),
        retry_at=NOW + timedelta(minutes=1),
        max_attempts=2,
    )
    assert retrying.status is AnalysisStatus.RETRY_WAIT
    assert retrying.error_code is AnalysisErrorCode.WORKER_LOST

    exhausted = claimed()
    exhausted.recover_expired_lease(
        NOW + timedelta(seconds=31),
        retry_at=NOW + timedelta(minutes=1),
        max_attempts=1,
    )
    assert exhausted.status is AnalysisStatus.FAILED
    assert exhausted.error_code is AnalysisErrorCode.WORKER_LOST


def test_ai_failure_is_terminal_only_for_the_analysis_job() -> None:
    value = claimed()
    value.fail(AnalysisErrorCode.INVALID_MODEL_OUTPUT, NOW, owner="worker-a")

    assert value.status is AnalysisStatus.FAILED
    assert value.artifact_id == "artifact-1"
    assert value.input_sha256 == SHA256
    assert value.error_code is AnalysisErrorCode.INVALID_MODEL_OUTPUT


def test_cancel_rejects_terminal_jobs() -> None:
    value = job()
    value.cancel(NOW)

    assert value.status is AnalysisStatus.CANCELLED
    assert value.error_code is AnalysisErrorCode.CANCELLED
    with pytest.raises(InvalidAnalysisTransition):
        value.cancel(NOW)
