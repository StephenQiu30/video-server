"""Pure resolution-job state machine boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from video_server.errors import DomainError

MAX_ATTEMPTS = 3


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class JobStage(StrEnum):
    VALIDATING_URL = "VALIDATING_URL"
    CHECKING_POLICY = "CHECKING_POLICY"
    EXTRACTING_METADATA = "EXTRACTING_METADATA"
    NORMALIZING_FORMATS = "NORMALIZING_FORMATS"
    READY = "READY"


class InvalidJobTransition(DomainError):
    """The requested transition violates the accepted job state machine."""


@dataclass(frozen=True, slots=True)
class JobState:
    status: JobStatus
    stage: JobStage
    attempt: int
    progress: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, JobStatus):
            raise TypeError("status must be a JobStatus")
        if not isinstance(self.stage, JobStage):
            raise TypeError("stage must be a JobStage")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int):
            raise TypeError("attempt must be an integer")
        if not 0 <= self.attempt <= MAX_ATTEMPTS:
            raise ValueError(f"attempt must be between 0 and {MAX_ATTEMPTS}")
        if self.progress is not None:
            if isinstance(self.progress, bool) or not isinstance(self.progress, int):
                raise TypeError("progress must be an integer or null")
            if not 0 <= self.progress <= 100:
                raise ValueError("progress must be between 0 and 100")
        if self.status is JobStatus.QUEUED and (
            self.stage is not JobStage.VALIDATING_URL
            or self.attempt != 0
            or self.progress is not None
        ):
            raise ValueError("queued state must be the untouched initial state")
        if (
            self.status in {JobStatus.RUNNING, JobStatus.RETRY_WAIT, JobStatus.SUCCEEDED}
            and self.attempt == 0
        ):
            raise ValueError("attempt must be positive after a job starts")
        if self.status is JobStatus.RETRY_WAIT and self.attempt >= MAX_ATTEMPTS:
            raise ValueError("retry-wait state cannot exceed the attempt limit")
        if self.status is JobStatus.SUCCEEDED:
            if self.stage is not JobStage.READY or self.progress != 100:
                raise ValueError("succeeded state must be READY at 100 progress")
        elif self.stage is JobStage.READY:
            raise ValueError("READY stage is reserved for succeeded jobs")
        if (
            self.status is JobStatus.FAILED
            and self.attempt == 0
            and (self.stage is not JobStage.VALIDATING_URL or self.progress is not None)
        ):
            raise ValueError("failed state before attempt 1 must preserve the initial snapshot")


_STAGE_ORDER = {stage: index for index, stage in enumerate(JobStage)}
_TERMINAL_STATUSES = frozenset({JobStatus.SUCCEEDED, JobStatus.FAILED})
_ALLOWED_STATUS_EDGES = {
    JobStatus.QUEUED: frozenset({JobStatus.RUNNING, JobStatus.FAILED}),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.RUNNING,
            JobStatus.RETRY_WAIT,
            JobStatus.SUCCEEDED,
            JobStatus.FAILED,
        }
    ),
    JobStatus.RETRY_WAIT: frozenset({JobStatus.RUNNING, JobStatus.FAILED}),
    JobStatus.SUCCEEDED: frozenset(),
    JobStatus.FAILED: frozenset(),
}


def _invalid(detail: str) -> InvalidJobTransition:
    return InvalidJobTransition("INVALID_JOB_TRANSITION", detail)


def transition(
    state: JobState,
    *,
    status: JobStatus,
    stage: JobStage | None = None,
    progress: int | None = None,
) -> JobState:
    if not isinstance(state, JobState):
        raise TypeError("state must be a JobState")
    if not isinstance(status, JobStatus):
        raise TypeError("status must be a JobStatus")
    if stage is not None and not isinstance(stage, JobStage):
        raise TypeError("stage must be a JobStage or null")
    if state.status in _TERMINAL_STATUSES:
        raise _invalid("terminal job states cannot transition")
    if status not in _ALLOWED_STATUS_EDGES[state.status]:
        raise _invalid(f"status transition {state.status} -> {status} is forbidden")

    if status is JobStatus.RETRY_WAIT:
        if state.attempt >= MAX_ATTEMPTS:
            raise _invalid("attempt limit reached; the job must fail")
        return JobState(status, state.stage, state.attempt, state.progress)

    if status is JobStatus.SUCCEEDED:
        return JobState(status, JobStage.READY, state.attempt, 100)

    if status is JobStatus.FAILED:
        return JobState(status, state.stage, state.attempt, state.progress)

    target_stage = stage if stage is not None else state.stage
    target_progress = progress if progress is not None else state.progress
    if _STAGE_ORDER[target_stage] < _STAGE_ORDER[state.stage]:
        raise _invalid("stage cannot move backward")
    if (
        state.progress is not None
        and target_progress is not None
        and target_progress < state.progress
    ):
        raise _invalid("progress cannot move backward")
    if target_stage is JobStage.READY:
        raise _invalid("stage READY is reserved for successful jobs")

    attempt = state.attempt
    if state.status in {JobStatus.QUEUED, JobStatus.RETRY_WAIT}:
        attempt += 1
    return JobState(status, target_stage, attempt, target_progress)
