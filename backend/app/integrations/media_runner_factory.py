"""Validated construction of anonymous and provider-isolated runner clients."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.core.config import Settings
from app.integrations.media_runner import MediaRunnerHttpClient, MediaRunnerRouter
from app.services.provider_route_admission import ProviderRouteAdmission
from app.services.provider_types import ProviderAccessContextRef, ProviderAccessMode
from app.workers.runner.provider_registry import provider_profile_for_key
from app.workers.runner.provider_session_policy import browser_session_policy


def anonymous_media_runner(
    settings: Settings, admission: ProviderRouteAdmission | None = None
) -> MediaRunnerHttpClient:
    return _media_runner(
        settings, settings.runner_base_url, admission, ProviderAccessMode.ANONYMOUS
    )


def operator_media_runners(
    settings: Settings,
    admission: ProviderRouteAdmission | None = None,
) -> dict[str, MediaRunnerHttpClient]:
    runners: dict[str, MediaRunnerHttpClient] = {}
    for provider, base_url in settings.runner_operator_base_urls.items():
        profile = provider_profile_for_key(provider)
        if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
            raise ValueError(f"provider does not allow operator access: {provider}")
        browser_session_policy(provider)
        runners[provider.value] = _media_runner(
            settings, base_url, admission, ProviderAccessMode.OPERATOR_MANAGED
        )
    return runners


def guest_media_runners(
    settings: Settings,
    admission: ProviderRouteAdmission | None = None,
    reject_guest: Callable[[ProviderAccessContextRef], Awaitable[None]] | None = None,
) -> dict[str, MediaRunnerHttpClient]:
    return {
        provider.value: _media_runner(
            settings, url, admission, ProviderAccessMode.GUEST, reject_guest
        )
        for provider, url in settings.runner_guest_base_urls.items()
    }


def media_runner_router(
    settings: Settings,
    admission: ProviderRouteAdmission | None = None,
    reject_guest: Callable[[ProviderAccessContextRef], Awaitable[None]] | None = None,
) -> MediaRunnerRouter:
    return MediaRunnerRouter(
        anonymous_media_runner(settings, admission),
        operator_media_runners(settings, admission),
        guests=guest_media_runners(settings, admission, reject_guest),
        default_policies=settings.runner_default_access_policies,
    )


def operator_provider_keys(settings: Settings) -> frozenset[str]:
    return frozenset(provider.value for provider in settings.runner_operator_base_urls)


def _media_runner(
    settings: Settings,
    base_url: str,
    admission: ProviderRouteAdmission | None,
    access_mode: ProviderAccessMode,
    reject_guest: Callable[[ProviderAccessContextRef], Awaitable[None]] | None = None,
) -> MediaRunnerHttpClient:
    return MediaRunnerHttpClient(
        base_url=base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
        admission=admission,
        expected_access_mode=access_mode,
        reject_guest=reject_guest,
    )
