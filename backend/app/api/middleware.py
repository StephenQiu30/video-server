"""HTTP admission and browser security policy for the public API."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse


async def request_guard(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    *,
    max_body_bytes: int,
    timeout_seconds: float,
    production: bool,
) -> Response:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_body_bytes:
                return _problem(
                    request,
                    413,
                    "request_too_large",
                    "Request body is too large.",
                    production=production,
                )
        except ValueError:
            return _problem(
                request,
                400,
                "invalid_request",
                "The request is invalid.",
                production=production,
            )
    try:
        async with asyncio.timeout(timeout_seconds):
            response = await call_next(request)
    except TimeoutError:
        return _problem(
            request,
            504,
            "request_timeout",
            "The request exceeded its deadline.",
            production=production,
        )
    _security_headers(response, production=production)
    return response


def _problem(
    request: Request,
    status: int,
    code: str,
    detail: str,
    *,
    production: bool,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"urn:video-server:error:{code}",
            "title": "Invalid request" if status < 500 else "Request failed",
            "status": status,
            "detail": detail,
            "code": code,
            "instance": request.url.path,
        },
    )
    _security_headers(response, production=production)
    return response


def _security_headers(response: Response, *, production: bool) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    response.headers.setdefault("Content-Security-Policy", _csp())
    if production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )


def _csp() -> str:
    return (
        "default-src 'self'; script-src 'self' 'unsafe-inline' "
        "https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
        "form-action 'self'"
    )
