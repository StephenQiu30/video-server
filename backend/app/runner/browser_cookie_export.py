"""Read and minimize one browser session into a provider-scoped secret."""

from __future__ import annotations

import os
import re
import stat
import tempfile
from collections.abc import Callable, Iterable
from http.cookiejar import Cookie, CookieJar, MozillaCookieJar
from pathlib import Path

from app.domain.providers import ProviderAccessMode
from app.runner.browser_cookie_source import (
    browser_profile_candidates as _browser_profile_candidates,
)
from app.runner.browser_cookie_source import (
    load_browser_cookies as _load_browser_cookies,
)
from app.runner.provider_registry import ProviderProfile, default_provider_registry

_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_AUTH_COOKIE_NAMES = {
    "youtube": frozenset(
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
    "tiktok": frozenset({"sessionid", "sessionid_ss", "sid_tt", "sid_guard", "uid_tt"}),
    "douyin": frozenset({"sessionid", "sessionid_ss", "sid_tt", "ttwid"}),
    "xiaohongshu": frozenset({"a1", "webId", "web_session"}),
    "reddit": frozenset({"loid", "reddit_session"}),
    "x": frozenset({"auth_token", "ct0"}),
    "instagram": frozenset({"sessionid"}),
    "facebook": frozenset({"c_user", "xs"}),
    "wechat_channels": frozenset({"hy_user", "hy_token"}),
}
type CookieLoader = Callable[[str, str | None], CookieJar]


class BrowserLoginRequiredError(ValueError):
    pass


def export_browser_cookies(
    *,
    provider: str,
    browser: str,
    profile: str | None,
    version: str,
    output_root: Path,
    cookie_loader: CookieLoader | None = None,
) -> tuple[Path, int]:
    provider_profile = _operator_profile(provider)
    if _VERSION.fullmatch(version) is None:
        raise ValueError("session version is invalid")
    if browser not in {"chrome", "chromium", "firefox"}:
        raise ValueError("browser must be Chrome, Chromium, or Firefox")
    root = _secure_directory(output_root.expanduser())
    provider_dir = _secure_directory(root / provider)
    jar = (
        cookie_loader(browser, profile)
        if cookie_loader is not None
        else _load_provider_browser_cookies(provider, browser, profile)
    )
    cookies = tuple(
        cookie
        for cookie in jar
        if not cookie.is_expired()
        and _domain_allowed(cookie.domain, provider_profile.cookie_domain_allowlist)
    )
    required_names = _AUTH_COOKIE_NAMES.get(provider, frozenset())
    cookie_names = {cookie.name for cookie in cookies}
    has_required_cookie = (
        required_names <= cookie_names
        if provider == "wechat_channels"
        else bool(required_names & cookie_names)
    )
    if not cookies or not has_required_cookie:
        raise BrowserLoginRequiredError(
            f"{provider} browser login cookie was not found"
        )
    target = provider_dir / f"{version}.cookies.txt"
    _write_cookie_jar(target, cookies)
    return target, len(cookies)


def supported_browser_session_providers() -> tuple[str, ...]:
    return tuple(sorted(_AUTH_COOKIE_NAMES))


def _load_provider_browser_cookies(
    provider: str,
    browser: str,
    profile: str | None,
) -> CookieJar:
    if profile is not None:
        return _load_browser_cookies(browser, profile)
    candidates = _browser_profile_candidates(browser)
    if not candidates:
        return _load_browser_cookies(browser, None)
    fallback: CookieJar | None = None
    last_error: OSError | None = None
    for candidate in candidates:
        try:
            jar = _load_browser_cookies(browser, str(candidate))
        except OSError as exc:
            last_error = exc
            continue
        fallback = jar
        if _has_provider_login_cookie(provider, jar):
            return jar
    if fallback is not None:
        return fallback
    if last_error is not None:
        raise last_error
    return _load_browser_cookies(browser, None)


def _has_provider_login_cookie(provider: str, jar: CookieJar) -> bool:
    required = _AUTH_COOKIE_NAMES.get(provider, frozenset())
    profile = _operator_profile(provider)
    names = {
        cookie.name
        for cookie in jar
        if not cookie.is_expired()
        and _domain_allowed(cookie.domain, profile.cookie_domain_allowlist)
    }
    return (
        required <= names if provider == "wechat_channels" else bool(required & names)
    )


def _operator_profile(provider: str) -> ProviderProfile:
    for profile in default_provider_registry().profiles:
        if profile.key == provider:
            if ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes:
                break
            return profile
    raise ValueError("provider does not support browser sessions")


def _secure_directory(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("session output directory cannot be a symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved = path.resolve()
    if not resolved.is_dir() or resolved.is_symlink():
        raise ValueError("session output directory must be a directory")
    os.chmod(resolved, 0o700)
    return resolved


def _domain_allowed(domain: str, allowlist: frozenset[str]) -> bool:
    normalized = domain.lstrip(".").casefold()
    return any(
        normalized == allowed or normalized.endswith(f".{allowed}")
        for allowed in allowlist
    )


def _write_cookie_jar(target: Path, cookies: Iterable[Cookie]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        dir=target.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        os.chmod(temporary, 0o600)
        jar = MozillaCookieJar(str(temporary))
        for cookie in cookies:
            jar.set_cookie(cookie)
        jar.save(ignore_discard=True, ignore_expires=True)
        os.chmod(temporary, stat.S_IRUSR)
        if target.exists():
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        try:
            os.replace(temporary, target)
        finally:
            if target.exists():
                os.chmod(target, stat.S_IRUSR)
    finally:
        temporary.unlink(missing_ok=True)
