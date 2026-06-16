import logging
from enum import StrEnum

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette import status

from app.core.responses import failure_response

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    """Centralized API-layer error codes for stable, machine-readable error semantics."""

    # Entry validation
    INVALID_URL = "invalid_url"
    UNSAFE_URL = "unsafe_url"

    # Parse / platform
    PARSE_FAILED = "parse_failed"
    PLATFORM_RESTRICTED = "platform_restricted"
    PLATFORM_RATE_LIMITED = "platform_rate_limited"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    PLATFORM_UNAVAILABLE = "platform_unavailable"

    # Infrastructure
    ENGINE_UNAVAILABLE = "engine_unavailable"
    QUEUE_UNAVAILABLE = "queue_unavailable"
    STORAGE_UNAVAILABLE = "storage_unavailable"

    # Auth
    INVALID_CREDENTIALS = "invalid_credentials"
    USER_DISABLED = "user_disabled"
    AUTH_LOCKED = "auth_locked"
    REGISTRATION_DISABLED = "registration_disabled"
    REGISTRATION_FAILED = "registration_failed"

    # Task lifecycle
    INVALID_STATE = "invalid_state"
    LIMIT_EXCEEDED = "limit_exceeded"
    NOT_FOUND = "not_found"
    RETENTION_EXPIRED = "retention_expired"
    RETRY_SUPERSEDED = "retry_superseded"

    # General
    RATE_LIMITED = "rate_limited"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"


class AppError(Exception):
    def __init__(self, code: str | ErrorCode, message: str, status_code: int = 400, details: str | dict | list | None = None):
        self.code = str(code)
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=failure_response(exc.code, exc.message, exc.details),
    )


async def http_exception_handler(_: Request, exc: HTTPException | StarletteHTTPException) -> JSONResponse:
    code, message = _http_error_contract(exc)
    return JSONResponse(status_code=exc.status_code, content=failure_response(code, message))


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=failure_response("validation_error", "请求参数不符合要求", exc.errors()),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled API exception path=%s method=%s request_id=%s",
        request.url.path,
        request.method,
        getattr(request.state, "request_id", None),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=failure_response("internal_error", "服务暂时不可用，请稍后重试"),
    )


def _http_error_contract(exc: HTTPException) -> tuple[str, str]:
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return "unauthorized", "请先登录后再继续操作"
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return "forbidden", "当前账号没有权限执行该操作"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return "not_found", "资源不存在"
    if exc.status_code >= 500:
        return "internal_error", "服务暂时不可用，请稍后重试"
    detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return "http_error", detail
