from __future__ import annotations

from enum import StrEnum


class AnalysisApplicationErrorCode(StrEnum):
    ARTIFACT_NOT_READY = "artifact_not_ready"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    INTERNAL_ERROR = "internal_error"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    INVALID_REQUEST = "invalid_request"
    INVALID_STATE = "invalid_state"
    NOT_FOUND = "not_found"
    PROVIDER_FAILURE = "provider_failure"
    RESOURCE_EXPIRED = "resource_expired"


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
