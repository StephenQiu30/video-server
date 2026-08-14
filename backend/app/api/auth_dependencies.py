"""Authentication, cookie and admission dependencies."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request, Response

from app.application.auth import (
    AuthError,
    AuthService,
    CurrentUser,
    SessionGrant,
    UserRole,
    UserService,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.infrastructure.rate_limiter import (
    RateLimiterUnavailable,
    RateLimitExceeded,
    ValkeyRateLimiter,
)

from .dependencies import get_runtime_settings


def get_auth_service(request: Request) -> AuthService:
    service = getattr(request.app.state, "auth_service", None)
    if service is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The authentication service is not available.",
        )
    return cast(AuthService, service)


def get_user_service(request: Request) -> UserService:
    service = getattr(request.app.state, "user_service", None)
    if service is None:
        raise AppError(
            status=503,
            code="service_unavailable",
            title="Service unavailable",
            detail="The user service is not available.",
        )
    return cast(UserService, service)


async def get_current_user(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> CurrentUser:
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    if access_token:
        try:
            user = await auth.current_user(access_token)
        except AuthError:
            user = None
    else:
        user = None
    if user is None:
        refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
        if not refresh_token:
            raise _unauthenticated()
        try:
            grant = await auth.refresh(refresh_token)
        except AuthError as exc:
            clear_auth_cookies(response, settings)
            raise _unauthenticated() from exc
        set_auth_cookies(response, settings, grant)
        user = grant.user
    operation = _rate_limit_operation(request)
    if operation is not None:
        await enforce_rate_limit(request, operation, user.owner_hash)
    return user


async def get_current_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if user.role is not UserRole.ADMIN:
        raise AppError(
            status=403,
            code="forbidden",
            title="Forbidden",
            detail="Administrator access is required.",
        )
    return user


async def enforce_rate_limit(request: Request, operation: str, owner_hash: str) -> None:
    limiter = cast(
        ValkeyRateLimiter | None,
        getattr(request.app.state, "rate_limiter", None),
    )
    if limiter is None:
        return
    client_host = request.client.host if request.client else "unknown"
    try:
        await limiter.check(
            operation=operation,
            owner_hash=owner_hash,
            client_host=client_host,
        )
    except RateLimitExceeded as exc:
        raise AppError(
            status=429,
            code="rate_limited",
            title="Too many requests",
            detail="The operation rate limit has been exceeded.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except RateLimiterUnavailable as exc:
        raise AppError(
            status=503,
            code="rate_limiter_unavailable",
            title="Service unavailable",
            detail="The operation admission service is unavailable.",
        ) from exc


def set_auth_cookies(
    response: Response, settings: Settings, grant: SessionGrant
) -> None:
    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=grant.access_token,
        max_age=settings.auth_access_token_ttl_seconds,
        httponly=True,
        secure=settings.app_env in {"staging", "production"},
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=grant.refresh_token,
        max_age=settings.auth_refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.app_env in {"staging", "production"},
        samesite="lax",
        path="/api/auth",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_access_cookie_name,
        httponly=True,
        secure=settings.app_env in {"staging", "production"},
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        httponly=True,
        secure=settings.app_env in {"staging", "production"},
        samesite="lax",
        path="/api/auth",
    )


def _unauthenticated() -> AppError:
    return AppError(
        status=401,
        code="unauthenticated",
        title="Authentication required",
        detail="Sign in to continue.",
    )


def _rate_limit_operation(request: Request) -> str | None:
    path = request.url.path.rstrip("/")
    if request.method == "DELETE" and path.startswith("/api/documents/"):
        return "document_import"
    if request.method != "POST":
        return None
    if path == "/api/inspections":
        return "inspect"
    if path == "/api/downloads":
        return "download"
    if path == "/api/media-imports":
        return "media_import"
    if path.startswith("/api/media-imports/") and path.endswith(
        ("/upload-sessions", "/complete")
    ):
        return "media_import_upload"
    if path == "/api/documents":
        return "document_import"
    if path.startswith("/api/documents/") and path.endswith(
        ("/upload-sessions", "/complete")
    ):
        return "document_import_upload"
    if path.endswith("/analyses") and path.startswith("/api/downloads/"):
        return "analysis"
    if path.startswith("/api/downloads/") and path.endswith("/retry"):
        # A retry re-runs an expensive runner re-inspection inside the HTTP
        # request, so it is an admission-bound operation like inspect/download.
        return "download_retry"
    return None
