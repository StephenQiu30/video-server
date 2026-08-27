"""RFC 9457 response mapping."""

from __future__ import annotations

from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse

from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
)
from app.application.auth import AuthError, AuthErrorCode
from app.application.downloads import ApplicationError, ApplicationErrorCode
from app.application.imports import (
    ImportApplicationError,
    ImportApplicationErrorCode,
)
from app.core.errors import AppError

_ERRORS: dict[ApplicationErrorCode, tuple[int, str, str]] = {
    ApplicationErrorCode.ARTICLE_ACCESS_RESTRICTED: (
        403,
        "Article access restricted",
        "The article requires a challenge, authentication, follow, or payment "
        "and cannot be discovered safely.",
    ),
    ApplicationErrorCode.ARTICLE_DISCOVERY_FAILED: (
        502,
        "Article discovery failed",
        "The public article could not be parsed within the safe discovery limits.",
    ),
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
    ApplicationErrorCode.PROVIDER_AUTH_REQUIRED: (
        422,
        "Provider session required",
        "This provider requires an approved session for the requested public media.",
    ),
    ApplicationErrorCode.PROVIDER_SESSION_EXPIRED: (
        422,
        "Provider session unavailable",
        "The approved provider session is no longer available. Try again later.",
    ),
    ApplicationErrorCode.PROVIDER_VERIFICATION_FAILED: (
        503,
        "Provider verification failed",
        "The provider could not verify this request. Try again later.",
    ),
    ApplicationErrorCode.PROVIDER_RATE_LIMITED: (
        429,
        "Provider rate limited",
        "The provider is temporarily rate limiting requests. Try again later.",
    ),
    ApplicationErrorCode.PROVIDER_GEO_RESTRICTED: (
        422,
        "Provider region restricted",
        "This media is not available from the configured service region.",
    ),
    ApplicationErrorCode.PROVIDER_CONTENT_RESTRICTED: (
        403,
        "Provider content restricted",
        "This media is private or requires an entitlement this service cannot use.",
    ),
    ApplicationErrorCode.PROVIDER_DRM_PROTECTED: (
        422,
        "DRM protected media",
        "DRM-protected media is outside the supported product boundary.",
    ),
    ApplicationErrorCode.PROVIDER_TEMPORARILY_UNAVAILABLE: (
        503,
        "Provider temporarily unavailable",
        "The provider adapter is temporarily degraded. Try again later.",
    ),
    ApplicationErrorCode.PROVIDER_LINK_UNAVAILABLE: (
        422,
        "Provider link unavailable",
        (
            "This sharing link no longer resolves to a playable video. "
            "Copy a fresh public sharing link and try again."
        ),
    ),
    ApplicationErrorCode.PROVIDER_MEDIA_UNSUPPORTED: (
        422,
        "Unsupported media type",
        (
            "The submitted link does not contain one supported video. "
            "Image and multi-attachment posts are not supported."
        ),
    ),
    ApplicationErrorCode.PROVIDER_UNSUPPORTED: (
        422,
        "Provider unsupported",
        "The current secure media runner does not support this provider.",
    ),
    ApplicationErrorCode.RESOURCE_EXPIRED: (
        404,
        "Not found",
        "The requested resource was not found.",
    ),
    ApplicationErrorCode.STORAGE_UNAVAILABLE: (
        503,
        "Storage unavailable",
        "The media preview is temporarily unavailable.",
    ),
}

_ANALYSIS_ERRORS: dict[AnalysisApplicationErrorCode, tuple[int, str, str]] = {
    AnalysisApplicationErrorCode.ALREADY_ACTIVE: (
        409,
        "Analysis already active",
        "The analysis already has an active execution run.",
    ),
    AnalysisApplicationErrorCode.ARTIFACT_UNAVAILABLE: (
        409,
        "Analysis artifact unavailable",
        "The original video artifact is no longer available for analysis.",
    ),
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
    AnalysisApplicationErrorCode.REPORT_NOT_READY: (
        409,
        "Analysis report not ready",
        "The analysis report has not finished publishing.",
    ),
    AnalysisApplicationErrorCode.REPORT_UNAVAILABLE: (
        503,
        "Analysis report unavailable",
        "The published analysis report could not be verified.",
    ),
    AnalysisApplicationErrorCode.RETRY_LIMITED: (
        429,
        "Analysis retry limited",
        "The analysis retry limit was reached. Try again later.",
    ),
    AnalysisApplicationErrorCode.SERVICE_UNAVAILABLE: (
        503,
        "Analysis unavailable",
        "Video analysis is not enabled for this deployment.",
    ),
}

_IMPORT_ERRORS: dict[ImportApplicationErrorCode, tuple[int, str, str]] = {
    ImportApplicationErrorCode.DISABLED: (
        503,
        "Media import unavailable",
        "Local media import is not enabled for this deployment.",
    ),
    ImportApplicationErrorCode.IDEMPOTENCY_CONFLICT: (
        409,
        "Idempotency conflict",
        "The idempotency key was already used for another request.",
    ),
    ImportApplicationErrorCode.INTERNAL_ERROR: (
        500,
        "Internal error",
        "The import request could not be completed.",
    ),
    ImportApplicationErrorCode.INVALID_REQUEST: (
        422,
        "Invalid import request",
        "The local file declaration is invalid.",
    ),
    ImportApplicationErrorCode.INVALID_STATE: (
        409,
        "Invalid import state",
        "The import cannot perform this operation in its current state.",
    ),
    ImportApplicationErrorCode.NOT_FOUND: (
        404,
        "Import not found",
        "The requested import resource was not found.",
    ),
    ImportApplicationErrorCode.SIZE_MISMATCH: (
        422,
        "Import size mismatch",
        "The uploaded object size differs from the declared file size.",
    ),
    ImportApplicationErrorCode.STORAGE_UNAVAILABLE: (
        503,
        "Import storage unavailable",
        "The upload storage is temporarily unavailable.",
    ),
    ImportApplicationErrorCode.UPLOAD_INCOMPLETE: (
        422,
        "Upload incomplete",
        "The multipart upload is incomplete or invalid.",
    ),
    ImportApplicationErrorCode.UPLOAD_SESSION_EXPIRED: (
        409,
        "Upload session expired",
        "Create a new upload session and retry the upload.",
    ),
}

_AUTH_ERRORS: dict[AuthErrorCode, tuple[int, str, str]] = {
    AuthErrorCode.EMAIL_ALREADY_REGISTERED: (
        409,
        "Email already registered",
        "An account with this email already exists.",
    ),
    AuthErrorCode.INVALID_CREDENTIALS: (
        401,
        "Invalid credentials",
        "The email or password is incorrect.",
    ),
    AuthErrorCode.USERNAME_ALREADY_REGISTERED: (
        409,
        "Username already registered",
        "This username is already in use.",
    ),
    AuthErrorCode.INVALID_USERNAME: (
        422,
        "Invalid username",
        "The username format is invalid.",
    ),
    AuthErrorCode.FORBIDDEN: (
        403,
        "Forbidden",
        "Administrator access is required.",
    ),
    AuthErrorCode.USER_NOT_FOUND: (
        404,
        "User not found",
        "The requested user does not exist.",
    ),
    AuthErrorCode.SELF_ADMIN_CHANGE: (
        409,
        "Self administration conflict",
        "Administrators cannot demote or disable their own account.",
    ),
    AuthErrorCode.UNAUTHENTICATED: (
        401,
        "Authentication required",
        "Sign in to continue.",
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


def import_application_error(error: ImportApplicationError) -> AppError:
    status, title, detail = _IMPORT_ERRORS[error.code]
    return AppError(
        status=status,
        code=error.code.value,
        title=title,
        detail=detail,
    )


def auth_application_error(error: AuthError) -> AppError:
    status, title, detail = _AUTH_ERRORS[error.code]
    return AppError(status=status, code=error.code.value, title=title, detail=detail)


async def app_error_handler(request: Request, error: Exception) -> JSONResponse:
    app_error = cast(AppError, error)
    return _problem_response(
        request,
        status=app_error.status,
        code=app_error.code,
        title=app_error.title,
        detail=app_error.detail,
        headers=app_error.headers,
    )


async def validation_error_handler(request: Request, _error: Exception) -> JSONResponse:
    return _problem_response(
        request,
        status=422,
        code="invalid_request",
        title="Invalid request",
        detail="The request parameters are invalid.",
    )


def _problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
        content={
            "type": f"urn:video-server:error:{code}",
            "title": title,
            "status": status,
            "detail": detail,
            "code": code,
            "instance": request.url.path,
        },
    )
