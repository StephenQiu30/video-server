from __future__ import annotations

import pytest

from video_server.job.state import (
    MAX_ATTEMPTS,
    InvalidJobTransition,
    JobStage,
    JobState,
    JobStatus,
    transition,
)


def _queued() -> JobState:
    return JobState(
        status=JobStatus.QUEUED,
        stage=JobStage.VALIDATING_URL,
        attempt=0,
        progress=None,
    )


def _running() -> JobState:
    return transition(
        _queued(),
        status=JobStatus.RUNNING,
        stage=JobStage.VALIDATING_URL,
        progress=0,
    )


def test_starting_and_retrying_increment_attempt_exactly_once() -> None:
    first_attempt = _running()
    waiting = transition(first_attempt, status=JobStatus.RETRY_WAIT)
    second_attempt = transition(waiting, status=JobStatus.RUNNING)

    assert first_attempt.attempt == 1
    assert waiting.attempt == 1
    assert second_attempt.attempt == 2


def test_running_job_can_only_move_stage_and_progress_forward() -> None:
    validating = _running()
    policy = transition(
        validating,
        status=JobStatus.RUNNING,
        stage=JobStage.CHECKING_POLICY,
        progress=20,
    )
    metadata = transition(
        policy,
        status=JobStatus.RUNNING,
        stage=JobStage.EXTRACTING_METADATA,
        progress=65,
    )

    assert metadata.stage is JobStage.EXTRACTING_METADATA
    assert metadata.progress == 65
    assert metadata.attempt == 1

    with pytest.raises(InvalidJobTransition, match="stage"):
        transition(
            metadata,
            status=JobStatus.RUNNING,
            stage=JobStage.CHECKING_POLICY,
            progress=70,
        )
    with pytest.raises(InvalidJobTransition, match="progress"):
        transition(
            metadata,
            status=JobStatus.RUNNING,
            stage=JobStage.NORMALIZING_FORMATS,
            progress=64,
        )


@pytest.mark.parametrize("progress", [-1, 101, 1.5, True])
def test_progress_is_null_or_a_non_boolean_integer_between_zero_and_100(
    progress: object,
) -> None:
    with pytest.raises((TypeError, ValueError), match="progress"):
        JobState(
            status=JobStatus.RUNNING,
            stage=JobStage.VALIDATING_URL,
            attempt=1,
            progress=progress,  # type: ignore[arg-type]
        )


def test_success_forces_ready_and_100_percent() -> None:
    normalizing = transition(
        _running(),
        status=JobStatus.RUNNING,
        stage=JobStage.NORMALIZING_FORMATS,
        progress=90,
    )
    succeeded = transition(normalizing, status=JobStatus.SUCCEEDED)

    assert succeeded.stage is JobStage.READY
    assert succeeded.progress == 100
    assert succeeded.attempt == 1


def test_failure_preserves_last_stage_progress_and_attempt() -> None:
    metadata = transition(
        _running(),
        status=JobStatus.RUNNING,
        stage=JobStage.EXTRACTING_METADATA,
        progress=55,
    )
    failed = transition(metadata, status=JobStatus.FAILED)

    assert failed.stage is JobStage.EXTRACTING_METADATA
    assert failed.progress == 55
    assert failed.attempt == 1


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (JobStatus.QUEUED, JobStatus.SUCCEEDED),
        (JobStatus.QUEUED, JobStatus.RETRY_WAIT),
        (JobStatus.RETRY_WAIT, JobStatus.SUCCEEDED),
    ],
)
def test_forbidden_status_edges_are_rejected(
    source: JobStatus,
    target: JobStatus,
) -> None:
    state = _queued()
    if source is JobStatus.RETRY_WAIT:
        state = transition(_running(), status=JobStatus.RETRY_WAIT)

    with pytest.raises(InvalidJobTransition, match="status"):
        transition(state, status=target)


@pytest.mark.parametrize("terminal_status", [JobStatus.SUCCEEDED, JobStatus.FAILED])
def test_terminal_states_are_irreversible(terminal_status: JobStatus) -> None:
    terminal = transition(_running(), status=terminal_status)

    with pytest.raises(InvalidJobTransition, match="terminal"):
        transition(terminal, status=JobStatus.RUNNING)


def test_third_attempt_must_fail_instead_of_waiting_for_a_fourth() -> None:
    running = _running()
    for _ in range(1, MAX_ATTEMPTS):
        running = transition(
            transition(running, status=JobStatus.RETRY_WAIT),
            status=JobStatus.RUNNING,
        )

    assert running.attempt == MAX_ATTEMPTS
    with pytest.raises(InvalidJobTransition, match="attempt"):
        transition(running, status=JobStatus.RETRY_WAIT)

    assert transition(running, status=JobStatus.FAILED).status is JobStatus.FAILED
