from __future__ import annotations

from app.domain.analysis import AnalysisErrorCode, AnalysisStage


class AnalysisOwnershipLost(RuntimeError):
    pass


class AnalysisLeaseLost(RuntimeError):
    pass


class AnalysisPersistenceUnavailable(RuntimeError):
    pass


class AnalysisSourceUnavailable(RuntimeError):
    pass


class AnalysisArtifactError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def classify_analysis_failure(
    error: BaseException, stage: AnalysisStage
) -> AnalysisErrorCode:
    code = getattr(error, "code", None)
    if code == "provider_rate_limited":
        return AnalysisErrorCode.PROVIDER_RATE_LIMITED
    if code in {"provider_unavailable", "provider_timeout"}:
        if stage is AnalysisStage.TRANSCRIBING and code == "provider_timeout":
            return AnalysisErrorCode.ASR_TIMEOUT
        return AnalysisErrorCode.PROVIDER_UNAVAILABLE
    if code in {"provider_invalid_response", "provider_rejected", "provider_refused"}:
        if stage is AnalysisStage.TRANSCRIBING:
            return AnalysisErrorCode.INVALID_TRANSCRIPT
        return AnalysisErrorCode.INVALID_MODEL_OUTPUT
    if code in {
        "media_probe_timeout",
        "audio_extraction_timeout",
    }:
        return AnalysisErrorCode.ASR_TIMEOUT
    if code in {
        "media_dependency_unavailable",
        "artifact_storage_unavailable",
        "invalid_analysis_workspace",
    }:
        return AnalysisErrorCode.WORKER_LOST
    if code in {
        "artifact_integrity_failed",
        "input_artifact_unavailable",
    }:
        return AnalysisErrorCode.INPUT_ARTIFACT_UNAVAILABLE
    if isinstance(code, str) and (
        code.startswith("invalid_")
        or code.endswith("_exceeded")
        or code in {"media_probe_failed", "audio_extraction_failed"}
    ):
        return AnalysisErrorCode.INVALID_TRANSCRIPT
    return AnalysisErrorCode.WORKER_LOST
