# ruff: noqa: B008
"""FastAPI dependencies and small service injection boundaries.

The application composition root installs concrete services in ``app.state``.
Keeping these lookups here lets contract tests replace them with in-memory
fakes without adding a second implementation of any business rule.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.errors import AppError
from src.core.security import (
    create_session_token,
    hash_session_token,
    require_same_origin,
    require_session_token,
    session_token_from_request,
)
from src.db.session import get_session_factory


@dataclass(frozen=True, slots=True)
class SessionIdentity:
    token: str
    token_hash: str
    is_new: bool = False


def get_request_settings(request: Request) -> Settings:
    configured = getattr(request.app.state, "settings", None)
    return configured if configured is not None else get_settings()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one transaction-scoped session for a request."""

    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def get_or_create_session_identity(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_request_settings),
) -> SessionIdentity:
    token = session_token_from_request(request, settings)
    if token is None:
        token = create_session_token()
        return SessionIdentity(token, hash_session_token(token), is_new=True)
    return SessionIdentity(token, hash_session_token(token))


def get_required_session_identity(
    request: Request,
    settings: Settings = Depends(get_request_settings),
) -> SessionIdentity:
    token = require_session_token(request, settings)
    return SessionIdentity(token, hash_session_token(token))


def set_new_session_cookie(
    identity: SessionIdentity,
    response: Response,
    settings: Settings,
) -> None:
    if identity.is_new:
        from src.core.security import set_session_cookie

        set_session_cookie(response, settings, identity.token)


def verify_post_origin(
    request: Request, settings: Settings = Depends(get_request_settings)
) -> None:
    require_same_origin(request, settings)


def _state_service(request: Request, names: tuple[str, ...]) -> Any:
    for name in names:
        value = getattr(request.app.state, name, None)
        if value is not None:
            return value
    raise AppError(
        "SERVICE_NOT_READY",
        "The requested service is not ready.",
        status_code=503,
    )


def get_media_service(request: Request) -> Any:
    return _state_service(request, ("media_service", "media_inspector"))


def get_download_service(request: Request) -> Any:
    return _state_service(request, ("download_service", "downloads"))


def get_queue_publisher(request: Request) -> Any | None:
    return getattr(request.app.state, "rabbitmq_publisher", None)


def get_readiness_checker(request: Request) -> Callable[[], Any] | None:
    checker = getattr(request.app.state, "readiness_checker", None)
    return checker if callable(checker) else None


async def maybe_await(value: Any) -> Any:
    if isinstance(value, Awaitable):
        return await value
    return value


__all__ = [
    "SessionIdentity",
    "get_db_session",
    "get_download_service",
    "get_media_service",
    "get_or_create_session_identity",
    "get_queue_publisher",
    "get_readiness_checker",
    "get_request_settings",
    "get_required_session_identity",
    "maybe_await",
    "set_new_session_cookie",
    "verify_post_origin",
]
