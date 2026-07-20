"""The persisted download-job state machine.

The database check constraints are the final guard.  This module provides the
same contract before a transaction is sent to PostgreSQL and makes illegal
rollback/retry transitions explicit to callers.
"""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


class JobStage(StrEnum):
    DOWNLOADING = "downloading"
    MERGING = "merging"
    VERIFYING = "verifying"
    UPLOADING = "uploading"


TERMINAL_STATUSES = frozenset(
    {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.EXPIRED}
)
ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.FAILED}),
    JobStatus.RUNNING: frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED}),
    JobStatus.SUCCEEDED: frozenset({JobStatus.EXPIRED}),
    JobStatus.FAILED: frozenset(),
    JobStatus.EXPIRED: frozenset(),
}


class InvalidTransition(ValueError):
    """Raised when a job state transition violates the product contract."""


def can_transition(current: JobStatus | str, target: JobStatus | str) -> bool:
    current_status = JobStatus(current)
    target_status = JobStatus(target)
    return target_status in ALLOWED_TRANSITIONS[current_status]


def assert_transition(current: JobStatus | str, target: JobStatus | str) -> None:
    current_status = JobStatus(current)
    target_status = JobStatus(target)
    if not can_transition(current_status, target_status):
        raise InvalidTransition(
            f"invalid download job transition: {current_status} -> {target_status}"
        )


def assert_stage(stage: JobStage | str | None) -> None:
    if stage is not None:
        JobStage(stage)
