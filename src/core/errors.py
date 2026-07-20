"""RFC 9457 Problem Details for every API failure path."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ProblemDetails(BaseModel):
    """The stable machine-readable error contract exposed by the API."""

    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    code: str
    details: Any | None = None


class AppError(Exception):
    """An expected, safe-to-return application error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Any | None = None,
        title: str | None = None,
        problem_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.title = title or _title_for_code(code)
        self.problem_type = problem_type or _problem_type(code)


def _problem_type(code: str) -> str:
    slug = code.strip().lower().replace("_", "-") or "application-error"
    return f"https://video.example/problems/{slug}"


def _title_for_code(code: str) -> str:
    return code.replace("_", " ").strip().title() or "Request failed"


def _safe_details(details: Any) -> Any:
    """Only retain JSON-like safe values; never include exception objects."""

    if details is None or isinstance(details, (str, int, float, bool)):
        return details
    if isinstance(details, Mapping):
        return {
            str(key): _safe_details(value)
            for key, value in details.items()
            if str(key).lower()
            not in {"url", "cookie", "authorization", "secret", "stack"}
        }
    if isinstance(details, (list, tuple)):
        return [_safe_details(item) for item in details]
    return None


def problem_response(
    *,
    status_code: int,
    code: str,
    detail: str,
    title: str | None = None,
    problem_type: str | None = None,
    details: Any | None = None,
) -> JSONResponse:
    """Build an ``application/problem+json`` response without an envelope."""

    problem = ProblemDetails(
        type=problem_type or _problem_type(code),
        title=title or _title_for_code(code),
        status=status_code,
        detail=detail,
        code=code,
        details=_safe_details(details),
    )
    payload = problem.model_dump(mode="json", exclude_none=True)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


async def app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Convert expected service errors into the stable Problem contract."""

    if not isinstance(exc, AppError):
        return problem_response(
            status_code=500,
            code="INTERNAL_ERROR",
            detail="An unexpected server error occurred.",
        )
    return problem_response(
        status_code=exc.status_code,
        code=exc.code,
        detail=exc.message,
        title=exc.title,
        problem_type=exc.problem_type,
        details=exc.details,
    )


async def request_validation_error_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Use 400 for malformed JSON/path/query input, never FastAPI's envelope."""

    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    fields = [".".join(str(part) for part in item.get("loc", ())) for item in errors]
    return problem_response(
        status_code=400,
        code="REQUEST_INVALID",
        detail="The request parameters are invalid.",
        details={"fields": fields} if fields else None,
    )


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Keep Starlette/FastAPI HTTP failures on the same wire contract."""

    if isinstance(exc, StarletteHTTPException):
        status = int(exc.status_code)
        detail = exc.detail if isinstance(exc.detail, str) else "The request failed."
    else:
        status = 500
        detail = "An unexpected server error occurred."
    return problem_response(
        status_code=status,
        code="HTTP_ERROR" if status < 500 else "INTERNAL_ERROR",
        detail=detail if status < 500 else "An unexpected server error occurred.",
    )


async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Redact stack details from clients while retaining server-side diagnostics."""

    logger.error(
        "unhandled_api_exception",
        extra={"exception_type": type(exc).__name__},
    )
    return problem_response(
        status_code=500,
        code="INTERNAL_ERROR",
        detail="An unexpected server error occurred.",
    )


__all__ = [
    "AppError",
    "ProblemDetails",
    "app_error_handler",
    "http_exception_handler",
    "problem_response",
    "request_validation_error_handler",
    "unhandled_exception_handler",
]
