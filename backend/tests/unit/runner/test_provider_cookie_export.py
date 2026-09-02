from __future__ import annotations

from http.cookiejar import Cookie, CookieJar

import pytest
from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.provider_cookie_export import export_provider_cookie_lease
from app.runner.provider_cookie_lease import ProviderCookieLeaseStatus
from app.runner.provider_session_policy import ProviderBrowserSessionPolicy


def _cookie(
    domain: str,
    *,
    name: str,
    value: str = "secret-value",
    expires: int | None = 2_000_000_000,
    http_only: bool = False,
) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=expires,
        discard=expires is None,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": None} if http_only else {},
        rfc2109=False,
    )


def _jar(*cookies: Cookie) -> CookieJar:
    jar = CookieJar()
    for cookie in cookies:
        jar.set_cookie(cookie)
    return jar


def test_export_uses_the_provider_policy_without_writing_a_session_file() -> None:
    captured: list[tuple[tuple[str, ...], str]] = []

    def load(policy: ProviderBrowserSessionPolicy, profile: str) -> CookieJar:
        captured.append((policy.domains, profile))
        return _jar(
            _cookie(".youtube.com", name="SID", http_only=True),
            _cookie("accounts.google.com", name="excluded"),
            _cookie("youtube.com", name="expired", expires=1),
        )

    result = export_provider_cookie_lease(
        provider=ProviderKey.YOUTUBE,
        profile="Default",
        version=ProviderSessionVersion.BROWSER,
        load=load,
        clock=lambda: 1_000,
    )

    assert result.status is ProviderCookieLeaseStatus.OK
    assert result.payload is not None
    payload = result.payload.decode()
    assert captured == [(("youtube-nocookie.com", "youtube.com"), "Default")]
    assert "#HttpOnly_.youtube.com" in payload
    assert "accounts.google.com" not in payload
    assert "expired" not in payload


def test_export_enforces_each_provider_required_cookie_set() -> None:
    result = export_provider_cookie_lease(
        provider=ProviderKey.INSTAGRAM,
        profile="Default",
        version=ProviderSessionVersion.BROWSER,
        load=lambda _policy, _profile: _jar(
            _cookie(".instagram.com", name="csrftoken")
        ),
    )

    assert result.status is ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED
    assert result.payload is None


def test_export_rejects_oversized_cookie_without_publishing_payload() -> None:
    result = export_provider_cookie_lease(
        provider=ProviderKey.YOUTUBE,
        profile="Default",
        version=ProviderSessionVersion.BROWSER,
        load=lambda _policy, _profile: _jar(
            _cookie("youtube.com", name="SID", value="x" * (1024**2))
        ),
    )

    assert result.status is ProviderCookieLeaseStatus.SESSION_UNAVAILABLE
    assert result.payload is None


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (FileNotFoundError(), "credential_required"),
        (RuntimeError("internal detail"), "provider_session_unavailable"),
    ),
)
def test_export_maps_browser_failures_to_stable_codes(
    error: Exception,
    expected: str,
) -> None:
    def fail(_policy: ProviderBrowserSessionPolicy, _profile: str) -> CookieJar:
        raise error

    assert export_provider_cookie_lease(
        provider=ProviderKey.YOUTUBE,
        profile="Default",
        version=ProviderSessionVersion.BROWSER,
        load=fail,
    ).status == ProviderCookieLeaseStatus(expected)
