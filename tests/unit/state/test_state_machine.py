import pytest
from src.downloads.state import (
    InvalidTransition,
    JobStage,
    JobStatus,
    assert_stage,
    assert_transition,
    can_transition,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (JobStatus.QUEUED, JobStatus.RUNNING),
        (JobStatus.QUEUED, JobStatus.FAILED),
        (JobStatus.RUNNING, JobStatus.SUCCEEDED),
        (JobStatus.RUNNING, JobStatus.FAILED),
        (JobStatus.SUCCEEDED, JobStatus.EXPIRED),
    ],
)
def test_allowed_transitions(current: JobStatus, target: JobStatus) -> None:
    assert can_transition(current, target)
    assert_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (JobStatus.QUEUED, JobStatus.SUCCEEDED),
        (JobStatus.RUNNING, JobStatus.QUEUED),
        (JobStatus.SUCCEEDED, JobStatus.RUNNING),
        (JobStatus.FAILED, JobStatus.QUEUED),
        (JobStatus.EXPIRED, JobStatus.FAILED),
    ],
)
def test_illegal_transitions_are_rejected(
    current: JobStatus, target: JobStatus
) -> None:
    assert not can_transition(current, target)
    with pytest.raises(InvalidTransition):
        assert_transition(current, target)


def test_stage_contract() -> None:
    for stage in JobStage:
        assert_stage(stage)
    assert_stage(None)
    with pytest.raises(ValueError):
        assert_stage("processing")
