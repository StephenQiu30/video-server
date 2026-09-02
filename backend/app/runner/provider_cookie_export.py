"""Export one provider-scoped Chrome Cookie jar as an in-memory lease."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable
from http.cookiejar import Cookie
from typing import Final

from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)
from app.runner.provider_session_policy import browser_session_policy
from app.runner.provider_session_source import (
    ProviderSessionLoader,
    load_provider_session,
)

OK: Final = ProviderCookieLeaseStatus.OK
CREDENTIAL_REQUIRED: Final = ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED
SESSION_UNAVAILABLE: Final = ProviderCookieLeaseStatus.SESSION_UNAVAILABLE

_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_CONTROL = frozenset("\t\r\n")
_MAX_COOKIE_BYTES = 1024**2


def export_provider_cookie_lease(
    *,
    provider: ProviderKey,
    profile: str,
    version: ProviderSessionVersion,
    load: ProviderSessionLoader = load_provider_session,
    clock: Callable[[], float] = time.time,
) -> ProviderCookieLease:
    """Return one allowlisted Cookie payload without retaining it on disk."""
    policy = browser_session_policy(provider)
    if version is not policy.version or _VERSION.fullmatch(version.value) is None:
        return ProviderCookieLease(SESSION_UNAVAILABLE)
    try:
        jar = load(policy, profile)
        now = int(clock())
        cookies = tuple(
            cookie for cookie in jar if eligible_cookie(cookie, policy.domains, now)
        )
        cookie_names = frozenset(cookie.name for cookie in cookies)
        if not cookies or not policy.accepts(cookie_names):
            return ProviderCookieLease(CREDENTIAL_REQUIRED)
        payload = cookie_payload(cookies)
    except FileNotFoundError:
        return ProviderCookieLease(CREDENTIAL_REQUIRED)
    except Exception:
        return ProviderCookieLease(SESSION_UNAVAILABLE)
    return ProviderCookieLease(OK, payload)


def eligible_cookie(cookie: Cookie, allowed_domains: Iterable[str], now: int) -> bool:
    domain = cookie.domain.lstrip(".").casefold()
    allowed = any(
        domain == item or domain.endswith(f".{item}") for item in allowed_domains
    )
    fields = (cookie.domain, cookie.path, cookie.name, cookie.value or "")
    return (
        allowed
        and not cookie.is_expired(now)
        and cookie.path.startswith("/")
        and all(not (_CONTROL & set(field)) for field in fields)
    )


def cookie_payload(cookies: tuple[Cookie, ...]) -> bytes:
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookies:
        name, value = cookie.name, cookie.value
        if value is None:
            name, value = "", name
        domain = cookie.domain
        if cookie.has_nonstandard_attr("HttpOnly"):
            domain = f"#HttpOnly_{domain}"
        lines.append(
            "\t".join(
                (
                    domain,
                    "TRUE" if cookie.domain.startswith(".") else "FALSE",
                    cookie.path,
                    "TRUE" if cookie.secure else "FALSE",
                    str(cookie.expires or 0),
                    name,
                    value,
                )
            )
        )
    payload = ("\n".join(lines) + "\n").encode()
    if len(payload) > _MAX_COOKIE_BYTES:
        raise OSError("Cookie payload exceeds the bounded session file size")
    return payload
