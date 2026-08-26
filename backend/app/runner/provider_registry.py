"""Strategy and registry primitives for media providers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import SplitResult, urlsplit

from app.domain.providers import (
    ProviderAccessMode,
    ProviderCapability,
    ProviderSupportStatus,
)
from app.runner.errors import RunnerFailure

UNSUPPORTED_PROVIDER_DOMAINS = frozenset(
    {
        "acfun.cn",
        "rutube.ru",
        "vk.com",
        "vk.ru",
        "vkvideo.ru",
        "dailymotion.com",
        "dai.ly",
        "nicovideo.jp",
        "nico.ms",
    }
)

UrlNormalizer = Callable[[str, SplitResult], str]


class ProviderRuntimeSettings(Protocol):
    runner_tiktok_device_id: str | None
    runner_youtube_pot_base_url: str | None


RuntimeCommandArgs = Callable[[ProviderRuntimeSettings], tuple[str, ...]]


def identity_url(url: str, _parsed: SplitResult) -> str:
    return url


def default_runtime_command_args(
    _settings: ProviderRuntimeSettings,
) -> tuple[str, ...]:
    return ()


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    key: str
    display_name: str
    hosts: frozenset[str]
    version: str = "1"
    capabilities: frozenset[ProviderCapability] = frozenset(
        {ProviderCapability.SINGLE_VIDEO}
    )
    access_modes: tuple[ProviderAccessMode, ...] = (ProviderAccessMode.ANONYMOUS,)
    cookie_domain_allowlist: frozenset[str] = frozenset()
    client_profile_id: str = "yt-dlp-default"
    attestation_policy: str = "none"
    egress_pool: str = "default"
    credential_concurrency: int = 0
    support_status: ProviderSupportStatus = ProviderSupportStatus.UNKNOWN
    canary_suite: str = "anonymous-metadata-range"
    error_policy_id: str = "yt-dlp-stable-v2"
    command_args: tuple[str, ...] = ()
    runtime_command_args: RuntimeCommandArgs = default_runtime_command_args
    inspection_attempts: int = 2
    inspection_retry_delay: float = 1.0
    normalize_url: UrlNormalizer = identity_url

    def request_url(self, url: str, parsed: SplitResult) -> str:
        return self.normalize_url(url, parsed)

    def command_args_for(
        self, settings: ProviderRuntimeSettings
    ) -> tuple[str, ...]:
        return (*self.command_args, *self.runtime_command_args(settings))


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """One resolved provider strategy reused throughout an operation."""

    source_url: str
    request_url: str
    profile: ProviderProfile


class ProviderRegistry:
    """Registry/Factory for matching a URL to an approved strategy."""

    def __init__(
        self,
        profiles: Iterable[ProviderProfile],
        *,
        fallback: ProviderProfile | None = None,
    ) -> None:
        configured = tuple(profiles)
        by_host: dict[str, ProviderProfile] = {}
        keys: set[str] = set()
        for profile in configured:
            if profile.key in keys:
                raise ValueError(f"provider key is registered twice: {profile.key}")
            keys.add(profile.key)
            if not profile.hosts:
                raise ValueError(f"provider {profile.key} must declare hosts")
            if profile.inspection_attempts < 1 or profile.inspection_retry_delay < 0:
                raise ValueError(f"provider {profile.key} has invalid retry policy")
            if (
                not profile.version
                or not profile.capabilities
                or not profile.access_modes
                or not profile.error_policy_id
                or not profile.canary_suite
            ):
                raise ValueError(f"provider {profile.key} has incomplete capabilities")
            supports_operator = (
                ProviderAccessMode.OPERATOR_MANAGED in profile.access_modes
            )
            if supports_operator != bool(profile.cookie_domain_allowlist):
                raise ValueError(f"provider {profile.key} has invalid session policy")
            if supports_operator != (profile.credential_concurrency > 0):
                raise ValueError(f"provider {profile.key} has invalid session limit")
            for host in profile.hosts:
                if host in by_host:
                    raise ValueError(f"provider host is registered twice: {host}")
                by_host[host] = profile
        self._profiles = configured
        self._by_host = by_host
        self._fallback = fallback or ProviderProfile(
            "generic",
            "Generic media source",
            frozenset(),
            support_status=ProviderSupportStatus.UNKNOWN,
            canary_suite="generic-public-fixtures",
        )

    @property
    def profiles(self) -> tuple[ProviderProfile, ...]:
        return self._profiles

    def resolve(self, url: str) -> ProviderProfile:
        hostname = urlsplit(url).hostname
        if hostname is not None and any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in UNSUPPORTED_PROVIDER_DOMAINS
        ):
            raise RunnerFailure("provider_unsupported", status=422)
        return (
            self._fallback
            if hostname is None
            else self._by_host.get(hostname, self._fallback)
        )

    def prepare(self, url: str) -> ProviderRequest:
        profile = self.resolve(url)
        return ProviderRequest(
            source_url=url,
            request_url=profile.request_url(url, urlsplit(url)),
            profile=profile,
        )


_DEFAULT_PROVIDER_REGISTRY: ProviderRegistry | None = None
_ACTIVE_PROVIDER_REGISTRY: ProviderRegistry | None = None


def default_provider_registry() -> ProviderRegistry:
    global _DEFAULT_PROVIDER_REGISTRY
    if _DEFAULT_PROVIDER_REGISTRY is None:
        from app.runner.provider_catalog import DEFAULT_PROVIDER_PROFILES

        _DEFAULT_PROVIDER_REGISTRY = ProviderRegistry(DEFAULT_PROVIDER_PROFILES)
    return _DEFAULT_PROVIDER_REGISTRY


def configure_provider_instances(peertube_hosts: frozenset[str]) -> None:
    """Replace the process-local registry during startup only."""
    global _ACTIVE_PROVIDER_REGISTRY
    if not peertube_hosts:
        _ACTIVE_PROVIDER_REGISTRY = None
        return
    from app.runner.provider_catalog_incremental import peertube_profile
    from app.runner.provider_instances import validated_instance_hosts

    profile = peertube_profile(validated_instance_hosts(peertube_hosts))
    _ACTIVE_PROVIDER_REGISTRY = ProviderRegistry(
        (*default_provider_registry().profiles, profile)
    )


def current_provider_registry() -> ProviderRegistry:
    return _ACTIVE_PROVIDER_REGISTRY or default_provider_registry()


def provider_profile(url: str) -> ProviderProfile:
    return current_provider_registry().resolve(url)


def provider_request(url: str) -> ProviderRequest:
    return current_provider_registry().prepare(url)
