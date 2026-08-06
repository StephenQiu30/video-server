from __future__ import annotations

from app.domain.downloads import DownloadErrorCode


class ExecutionPersistenceUnavailable(RuntimeError):
    pass


class ExecutionSourceUnavailable(RuntimeError):
    pass


class ExecutionOwnershipLost(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


class LeaseInfrastructureError(RuntimeError):
    pass


class ArtifactValidationError(RuntimeError):
    pass


_RUNNER_CODES = {
    "download_timeout": DownloadErrorCode.DOWNLOAD_TIMEOUT,
    "inspection_timeout": DownloadErrorCode.INSPECTION_TIMEOUT,
    "format_unavailable": DownloadErrorCode.FORMAT_UNAVAILABLE,
    "transcode_required": DownloadErrorCode.TRANSCODE_REQUIRED,
    "media_validation_failed": DownloadErrorCode.MEDIA_VALIDATION_FAILED,
    "invalid_artifact_path": DownloadErrorCode.MEDIA_VALIDATION_FAILED,
    "invalid_runner_response": DownloadErrorCode.MEDIA_VALIDATION_FAILED,
    "workspace_limit_exceeded": DownloadErrorCode.OUTPUT_LIMIT_EXCEEDED,
    "output_limit_exceeded": DownloadErrorCode.OUTPUT_LIMIT_EXCEEDED,
    "source_changed": DownloadErrorCode.UNSUPPORTED_SOURCE,
    "unsupported_source": DownloadErrorCode.UNSUPPORTED_SOURCE,
    "unsupported_url": DownloadErrorCode.UNSUPPORTED_SOURCE,
    "runner_dependency_unavailable": DownloadErrorCode.WORKER_LOST,
    "runner_unavailable": DownloadErrorCode.WORKER_LOST,
    "runner_busy": DownloadErrorCode.WORKER_LOST,
    "task_not_found": DownloadErrorCode.WORKER_LOST,
    "cancelled": DownloadErrorCode.WORKER_LOST,
}


def classify_runner_failure(error: BaseException) -> DownloadErrorCode:
    code = getattr(error, "code", None)
    if isinstance(code, str):
        return _RUNNER_CODES.get(code, DownloadErrorCode.WORKER_LOST)
    return DownloadErrorCode.WORKER_LOST
