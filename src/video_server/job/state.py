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


def transition(
    state: JobState,
    *,
    status: JobStatus,
    stage: JobStage | None = None,
    progress: int | None = None,
) -> JobState:
    raise NotImplementedError("job transitions are not implemented")
