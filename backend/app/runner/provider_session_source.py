"""Deterministic source adapters for provider-scoped browser sessions."""

from __future__ import annotations

from collections.abc import Callable
from http.cookiejar import CookieJar

from app.runner.chrome_provider_cookies import extract_chrome_cookies
from app.runner.ephemeral_yuanbao_session import EphemeralYuanbaoSession
from app.runner.provider_session_policy import (
    ProviderBrowserSessionPolicy,
    ProviderSessionSource,
)

type ProviderSessionLoader = Callable[[ProviderBrowserSessionPolicy, str], CookieJar]


def load_provider_session(
    policy: ProviderBrowserSessionPolicy,
    profile: str,
) -> CookieJar:
    if policy.source is ProviderSessionSource.CHROME_PROFILE:
        return extract_chrome_cookies(policy.domains, profile)
    if policy.source is ProviderSessionSource.EPHEMERAL_YUANBAO:
        return EphemeralYuanbaoSession(profile).load()
    raise ValueError("unsupported provider session source")
