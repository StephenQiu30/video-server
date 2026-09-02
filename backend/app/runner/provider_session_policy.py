"""Central policy for browser-backed operator sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.errors import RunnerFailure
from app.runner.provider_registry import provider_profile_for_key


class CookieRequirement(StrEnum):
    ANY = "any"
    ALL = "all"


class ProviderSessionSource(StrEnum):
    CHROME_PROFILE = "chrome_profile"
    EPHEMERAL_YUANBAO = "ephemeral_yuanbao"


@dataclass(frozen=True, slots=True)
class ProviderBrowserSessionPolicy:
    provider: ProviderKey
    version: ProviderSessionVersion
    required_cookie_names: frozenset[str]
    requirement: CookieRequirement = CookieRequirement.ANY
    source: ProviderSessionSource = ProviderSessionSource.CHROME_PROFILE

    @property
    def domains(self) -> tuple[str, ...]:
        profile = provider_profile_for_key(self.provider)
        return tuple(sorted(str(domain) for domain in profile.cookie_domain_allowlist))

    def accepts(self, cookie_names: frozenset[str]) -> bool:
        if self.requirement is CookieRequirement.ALL:
            return self.required_cookie_names <= cookie_names
        return bool(self.required_cookie_names & cookie_names)


_BROWSER_SESSION_POLICIES = {
    policy.provider: policy
    for policy in (
        ProviderBrowserSessionPolicy(
            ProviderKey.YOUTUBE,
            ProviderSessionVersion.BROWSER,
            frozenset(
                {
                    "SID",
                    "HSID",
                    "SSID",
                    "APISID",
                    "SAPISID",
                    "__Secure-1PSID",
                    "__Secure-3PSID",
                }
            ),
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.DOUYIN,
            ProviderSessionVersion.BROWSER,
            frozenset({"sessionid", "sessionid_ss", "sid_tt", "ttwid"}),
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.XIAOHONGSHU,
            ProviderSessionVersion.BROWSER,
            frozenset({"a1", "webId", "web_session"}),
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.X,
            ProviderSessionVersion.BROWSER,
            frozenset({"auth_token", "ct0"}),
            CookieRequirement.ALL,
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.INSTAGRAM,
            ProviderSessionVersion.BROWSER,
            frozenset({"sessionid"}),
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.FACEBOOK,
            ProviderSessionVersion.BROWSER,
            frozenset({"c_user", "xs"}),
            CookieRequirement.ALL,
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.REDDIT,
            ProviderSessionVersion.BROWSER,
            frozenset({"loid", "reddit_session"}),
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.PINTEREST,
            ProviderSessionVersion.BROWSER,
            frozenset({"_auth", "_pinterest_sess"}),
            CookieRequirement.ALL,
        ),
        ProviderBrowserSessionPolicy(
            ProviderKey.WECHAT_CHANNELS,
            ProviderSessionVersion.BROWSER,
            frozenset({"hy_user", "hy_token"}),
            CookieRequirement.ALL,
            ProviderSessionSource.EPHEMERAL_YUANBAO,
        ),
    )
}


def browser_session_policy(
    provider: str | ProviderKey,
) -> ProviderBrowserSessionPolicy:
    try:
        key = ProviderKey(provider)
        return _BROWSER_SESSION_POLICIES[key]
    except (KeyError, ValueError) as exc:
        raise RunnerFailure("provider_session_not_allowed", status=422) from exc


def browser_session_providers() -> frozenset[ProviderKey]:
    return frozenset(_BROWSER_SESSION_POLICIES)
