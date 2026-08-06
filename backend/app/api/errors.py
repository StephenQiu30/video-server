"""RFC 9457 response mapping."""

from __future__ import annotations

from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
)
from app.application.downloads import ApplicationError, ApplicationErrorCode
from app.core.errors import AppError

_ERRORS: dict[ApplicationErrorCode, tuple[int, str, str]] = {
    ApplicationErrorCode.DOWNLOAD_NOT_READY: (
        409,
        "Download not ready",
        "The download is not ready for file delivery.",
    ),
    ApplicationErrorCode.DURATION_LIMIT_EXCEEDED: (
        422,
        "Duration limit exceeded",
        "The media exceeds the configured duration limit.",
    ),
    ApplicationErrorCode.FORMAT_UNAVAILABLE: (
        422,
        "Format unavailable",
        "No supported semantic download format is available.",
    ),
    ApplicationErrorCode.IDEMPOTENCY_CONFLICT: (
        409,
        "Idempotency conflict",
        "The idempotency key was already used for another request.",
    ),
    ApplicationErrorCode.INSPECTION_FAILED: (
        502,
        "Inspection failed",
        "The media provider could not be inspected.",
    ),
    ApplicationErrorCode.INSPECTION_TIMEOUT: (
        504,
        "Inspection timed out",
        "The media inspection exceeded its deadline.",
    ),
    ApplicationErrorCode.INTERNAL_ERROR: (
        500,
        "Internal error",
        "The request could not be completed.",
    ),
    ApplicationErrorCode.INVALID_REQUEST: (
        422,
        "Invalid request",
        "The request parameters are invalid.",
    ),
    ApplicationErrorCode.INVALID_STATE: (
        409,
        "Invalid state",
        "The resource cannot perform this operation in its current state.",
    ),
    ApplicationErrorCode.INVALID_URL: (
        422,
        "Invalid URL",
        "The submitted media URL is not allowed.",
    ),
    ApplicationErrorCode.NOT_FOUND: (
        404,
        "Not found",
        "The requested resource was not found.",
    ),
    ApplicationErrorCode.RESOURCE_EXPIRED: (
        404,
        "Not found",
        "The requested resource was not found.",
    ),
}

_ANALYSIS_ERRORS: dict[AnalysisApplicationErrorCode, tuple[int, str, str]] = {
    AnalysisApplicationErrorCode.ARTIFACT_NOT_READY: (
        409,
        "Artifact not ready",
        "The download artifact is not ready for analysis.",
    ),
    AnalysisApplicationErrorCode.IDEMPOTENCY_CONFLICT: (
        409,
        "Idempotency conflict",
        "The idempotency key was already used for another request.",
    ),
    AnalysisApplicationErrorCode.INTERNAL_ERROR: (
        500,
        "Internal error",
        "The request could not be completed.",
    ),
    AnalysisApplicationErrorCode.INVALID_MODEL_OUTPUT: (
        502,
        "Invalid model output",
        "The analysis provider returned an invalid result.",
    ),
    AnalysisApplicationErrorCode.INVALID_REQUEST: (
        422,
        "Invalid request",
        "The request parameters are invalid.",
    ),
    AnalysisApplicationErrorCode.INVALID_STATE: (
        409,
        "Invalid state",
        "The analysis cannot perform this operation in its current state.",
    ),
    AnalysisApplicationErrorCode.NOT_FOUND: (
        404,
        "Not found",
        "The requested resource was not found.",
    ),
    AnalysisApplicationErrorCode.PROVIDER_FAILURE: (
        502,
        "Analysis provider failure",
        "The analysis provider could not complete the request.",
    ),
    AnalysisApplicationErrorCode.RESOURCE_EXPIRED: (
        404,
        "Not found",
        "The requested resource was not found.",
    ),
}


def application_error(error: ApplicationError) -> AppError:
    status, title, detail = _ERRORS[error.code]
    return AppError(
        status=status,
        code=error.code.value,
        title=title,
        detail=detail,
    )


def analysis_application_error(error: AnalysisApplicationError) -> AppError:
    status, title, detail = _ANALYSIS_ERRORS[error.code]
    return AppError(
        status=status,
        code=error.code.value,
        title=title,
        detail=detail,
    )


async def app_error_handler(request: Request, error: Exception) -> JSONResponse:
    app_error = cast(AppError, error)
    return JSONResponse(
        status_code=app_error.status,
        media_type="application/problem+json",
        content={
            "type": f"urn:video-server:error:{app_error.code}",
            "title": app_error.title,
            "status": app_error.status,
            "detail": app_error.detail,
            "code": app_error.code,
            "instance": request.url.path,
        },
    )
