"""Validation rules for AI analysis Provider profiles."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

from app.application.auth import CurrentUser, UserRole

from .ai_provider_models import (
    AiProviderAuthMode,
    AiProviderEngine,
    AiProviderError,
    AiProviderErrorCode,
)

_KEY = re.compile(r"[a-z][a-z0-9_-]{0,31}")


def require_admin(actor: CurrentUser) -> None:
    if actor.role is not UserRole.ADMIN:
        raise AiProviderError(AiProviderErrorCode.FORBIDDEN)


def validated_profile(
    *,
    key: str,
    display_name: str,
    engine: AiProviderEngine,
    auth_mode: AiProviderAuthMode,
    base_url: str | None,
    model: str,
    api_key: str | None,
    require_api_key: bool,
) -> tuple[str, str, str | None, str]:
    del engine
    if auth_mode is AiProviderAuthMode.API_KEY and require_api_key:
        if api_key is None or not api_key.strip():
            raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    if api_key is not None and len(api_key.strip()) > 4096:
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    return (
        validated_key(key),
        validated_name(display_name),
        validated_base_url(base_url, auth_mode),
        validated_model(model),
    )


def validated_key(key: str) -> str:
    normalized = key.strip().casefold()
    if _KEY.fullmatch(normalized) is None:
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    return normalized


def validated_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not 1 <= len(normalized) <= 64:
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    return normalized


def validated_model(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 128 or any(ord(char) < 32 for char in normalized):
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    return normalized


def validated_base_url(value: str | None, auth_mode: AiProviderAuthMode) -> str | None:
    if auth_mode is AiProviderAuthMode.HOST_LOGIN:
        if value is not None and value.strip():
            raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
        return None
    if value is None:
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    try:
        parsed = urlsplit(value.strip())
        _ = parsed.port
    except ValueError as exc:
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE) from exc
    loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.scheme not in ({"http", "https"} if loopback else {"https"})
    ):
        raise AiProviderError(AiProviderErrorCode.INVALID_PROFILE)
    return urlunsplit(parsed._replace(path=parsed.path.rstrip("/")))
