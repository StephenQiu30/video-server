from __future__ import annotations

from urllib.parse import urlsplit

from app.runner.provider_registry import provider_profile


def provider_request_url(url: str) -> str:
    """Return the provider strategy's canonical request URL."""
    profile = provider_profile(url)
    return profile.request_url(url, urlsplit(url))


def provider_command_args(url: str) -> tuple[str, ...]:
    """Return only the fixed arguments approved for the matched provider."""
    return provider_profile(url).command_args


def provider_inspection_attempts(url: str) -> int:
    return provider_profile(url).inspection_attempts


def provider_inspection_retry_delay(url: str) -> float:
    return provider_profile(url).inspection_retry_delay
