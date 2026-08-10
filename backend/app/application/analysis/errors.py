from __future__ import annotations

from enum import StrEnum


class AnalysisApplicationErrorCode(StrEnum):
    ALREADY_ACTIVE = "analysis_already_active"
    ARTIFACT_UNAVAILABLE = "analysis_artifact_unavailable"
    ARTIFACT_NOT_READY = "artifact_not_ready"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    INTERNAL_ERROR = "internal_error"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    NOT_FOUND = "not_found"
    PROVIDER_FAILURE = "provider_failure"
    REPORT_NOT_READY = "analysis_report_not_ready"
    REPORT_UNAVAILABLE = "analysis_report_unavailable"
    RETRY_LIMITED = "analysis_retry_limited"
    RESOURCE_EXPIRED = "resource_expired"
    SERVICE_UNAVAILABLE = "analysis_unavailable"


class AnalysisApplicationError(RuntimeError):
    def __init__(self, code: AnalysisApplicationErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class PersistenceIdempotencyConflict(RuntimeError):
    """An idempotency key was reused with a different request fingerprint."""


class PersistenceConflict(RuntimeError):
    """An expected job version or lease precondition was lost."""


class PersistenceNotFound(RuntimeError):
    """An analysis persistence projection could not be found."""


class PersistenceActiveRun(PersistenceConflict):
    """The stable analysis job already has an active execution run."""


class PersistenceArtifactUnavailable(PersistenceConflict):
    """The immutable input artifact can no longer be analyzed."""


class PersistenceRetryLimited(PersistenceConflict):
    """A stable manual retry run or owner frequency limit was reached."""
