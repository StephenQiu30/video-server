"""Strategy and registry primitives for media providers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from app.domain.providers import (
    ProviderAccessMode,
    ProviderCapability,
    ProviderSupportStatus,
)

UrlNormalizer = Callable[[str, SplitResult], str]


def _identity(url: str, _parsed: SplitResult) -> str:
    return url


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
    inspection_attempts: int = 2
    inspection_retry_delay: float = 1.0
    normalize_url: UrlNormalizer = _identity

    def request_url(self, url: str, parsed: SplitResult) -> str:
        return self.normalize_url(url, parsed)


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
        for profile in configured:
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
        return (
            self._fallback
            if hostname is None
            else self._by_host.get(hostname, self._fallback)
        )


from app.runner.provider_catalog import DEFAULT_PROVIDER_PROFILES  # noqa: E402

DEFAULT_PROVIDER_REGISTRY = ProviderRegistry(DEFAULT_PROVIDER_PROFILES)


def provider_profile(url: str) -> ProviderProfile:
    return DEFAULT_PROVIDER_REGISTRY.resolve(url)
