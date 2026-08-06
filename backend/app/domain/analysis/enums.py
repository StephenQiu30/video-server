from __future__ import annotations

from enum import StrEnum


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisStage(StrEnum):
    PREPARING = "preparing"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    VALIDATING = "validating"


class AnalysisErrorCode(StrEnum):
    CANCELLED = "cancelled"
    ASR_TIMEOUT = "asr_timeout"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    INVALID_TRANSCRIPT = "invalid_transcript"
    INPUT_ARTIFACT_UNAVAILABLE = "input_artifact_unavailable"
    INTERNAL_ERROR = "internal_error"
    WORKER_LOST = "worker_lost"

    @property
    def retryable(self) -> bool:
        return self in {
            self.ASR_TIMEOUT,
            self.PROVIDER_RATE_LIMITED,
            self.PROVIDER_UNAVAILABLE,
            self.WORKER_LOST,
        }


class AnalysisValidationCode(StrEnum):
    INVALID_SCHEMA = "invalid_schema"
    INVALID_TEXT = "invalid_text"
    INVALID_EVIDENCE = "invalid_evidence"
    INVALID_TIME_RANGE = "invalid_time_range"
    DUPLICATE_IDENTIFIER = "duplicate_identifier"
    LIMIT_EXCEEDED = "limit_exceeded"
