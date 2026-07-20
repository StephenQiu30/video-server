"""Small security helpers shared by HTTP and worker logging paths.

The API deliberately keeps the anonymous session primitive tiny: the browser
holds a random 256-bit value and PostgreSQL only receives its SHA-256 digest.
No token is ever put into a URL, response log, or error payload.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from fastapi import Request, Response

from src.core.errors import AppError

SESSION_TOKEN_BYTES = 32


def redact_value(value: object) -> str:
    """Hide credentials and secrets from logs and error payloads."""

    if value is None:
        return "***"
    return "***" if str(value) else "***"


def redact_url(value: str) -> str:
    """Return a URL safe for logs: no credentials, query or fragment."""

    try:
        parsed = urlsplit(value)
        if not parsed.scheme or not parsed.netloc:
            return "[redacted-url]"
        hostname = parsed.hostname or ""
        host = (
            f"[{hostname}]"
            if ":" in hostname and not hostname.startswith("[")
            else hostname
        )
        if parsed.port:
            host = f"{host}:{parsed.port}"
        safe = SplitResult(parsed.scheme, host, parsed.path, "", "")
        return urlunsplit(safe)
    except ValueError:
        return "[redacted-url]"


def create_session_token() -> str:
    """Create a URL-safe random token with 256 bits of entropy."""

    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """Return the only token representation persisted by the service."""

    if not token:
        raise ValueError("session token must not be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, settings: Any, token: str) -> None:
    """Set the anonymous session cookie with the fixed MVP attributes."""

    response.set_cookie(
        key=str(settings.session_cookie_name),
        value=token,
        max_age=int(settings.session_ttl_seconds),
        expires=int(settings.session_ttl_seconds),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def session_token_from_request(request: Request, settings: Any) -> str | None:
    """Read the cookie without accepting alternate headers or query values."""

    value = request.cookies.get(str(settings.session_cookie_name))
    return value if value else None


def require_session_token(request: Request, settings: Any) -> str:
    """Return the current cookie or raise a safe RFC 9457 application error."""

    token = session_token_from_request(request, settings)
    if token is None:
        raise AppError(
            "SESSION_REQUIRED",
            "A valid video session is required.",
            status_code=403,
        )
    return token


def _normalise_origin(value: str) -> str:
    """Normalise only scheme/host/port; paths and credentials are rejected."""

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.hostname or parsed.username or parsed.password:
        return ""
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return ""
    try:
        port = parsed.port
    except ValueError:
        return ""
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower().rstrip(".")
    default_port = 443 if scheme == "https" else 80
    suffix = f":{port}" if port and port != default_port else ""
    return f"{scheme}://{host}{suffix}"


def is_allowed_origin(origin: str | None, expected_origin: str) -> bool:
    """Return whether an Origin header exactly matches the configured web app."""

    if origin is None:
        return False
    actual = _normalise_origin(origin)
    expected = _normalise_origin(expected_origin)
    return bool(actual and expected and secrets.compare_digest(actual, expected))


def require_same_origin(request: Request, settings: Any) -> None:
    """Enforce the POST Origin boundary used by the browser MVP client."""

    origin = request.headers.get("origin")
    expected = str(settings.web_origin)
    if not is_allowed_origin(origin, expected):
        raise AppError(
            "ORIGIN_FORBIDDEN",
            "The request origin is not allowed.",
            status_code=403,
        )


def safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a log-safe subset of headers for diagnostics."""

    sensitive = {"authorization", "cookie", "set-cookie", "x-api-key"}
    return {
        key.lower(): "***" if key.lower() in sensitive else value
        for key, value in headers.items()
    }
