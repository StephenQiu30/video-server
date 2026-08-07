"""Strategy and registry primitives for media providers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

UrlNormalizer = Callable[[str, SplitResult], str]


def _identity(url: str, _parsed: SplitResult) -> str:
    return url


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    key: str
    display_name: str
    hosts: frozenset[str]
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
            for host in profile.hosts:
                if host in by_host:
                    raise ValueError(f"provider host is registered twice: {host}")
                by_host[host] = profile
        self._by_host = by_host
        self._fallback = fallback or ProviderProfile(
            "generic", "Generic media source", frozenset()
        )

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
