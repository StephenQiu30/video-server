"""Validated construction of anonymous and provider-isolated runner clients."""

from __future__ import annotations

from app.core.config import Settings
from app.domain.providers import ProviderAccessMode
from app.infrastructure.media_runner import (
    MediaRunnerHttpClient,
    MediaRunnerRouter,
)
from app.runner.provider_registry import provider_profile_for_key
from app.runner.provider_session_policy import browser_session_policy


def anonymous_media_runner(settings: Settings) -> MediaRunnerHttpClient:
    return _media_runner(settings, settings.runner_base_url)


def operator_media_runners(
    settings: Settings,
) -> dict[str, MediaRunnerHttpClient]:
    runners: dict[str, MediaRunnerHttpClient] = {}
    for provider, base_url in settings.runner_operator_base_urls.items():
        profile = provider_profile_for_key(provider)
        if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
            raise ValueError(f"provider does not allow operator access: {provider}")
        browser_session_policy(provider)
        runners[provider.value] = _media_runner(settings, base_url)
    return runners


def media_runner_router(settings: Settings) -> MediaRunnerRouter:
    return MediaRunnerRouter(
        anonymous_media_runner(settings),
        operator_media_runners(settings),
    )


def operator_provider_keys(settings: Settings) -> frozenset[str]:
    return frozenset(provider.value for provider in settings.runner_operator_base_urls)


def _media_runner(settings: Settings, base_url: str) -> MediaRunnerHttpClient:
    return MediaRunnerHttpClient(
        base_url=base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
