"""Export a browser session into a provider-scoped Docker secret."""

from __future__ import annotations

import argparse
import os
import re
import stat
import tempfile
from collections.abc import Callable, Iterable
from http.cookiejar import Cookie, CookieJar, MozillaCookieJar
from pathlib import Path
from typing import cast

from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

from app.domain.providers import ProviderAccessMode
from app.runner.provider_registry import DEFAULT_PROVIDER_REGISTRY, ProviderProfile

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
}
type CookieLoader = Callable[[str, str | None], CookieJar]


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
    jar = (cookie_loader or _load_browser_cookies)(browser, profile)
    cookies = tuple(
        cookie
        for cookie in jar
        if not cookie.is_expired()
        and _domain_allowed(cookie.domain, provider_profile.cookie_domain_allowlist)
    )
    required_names = _AUTH_COOKIE_NAMES.get(provider, frozenset())
    if not cookies or not any(cookie.name in required_names for cookie in cookies):
        raise ValueError(f"{provider} browser login cookie was not found")
    target = provider_dir / f"{version}.cookies.txt"
    _write_cookie_jar(target, cookies)
    return target, len(cookies)


def _load_browser_cookies(browser: str, profile: str | None) -> CookieJar:
    specification = (browser, profile, None, None)
    with YoutubeDL(
        {
            "cookiesfrombrowser": specification,
            "quiet": True,
            "no_warnings": True,
        }
    ) as ydl:
        return cast(CookieJar, ydl.cookiejar)


def _operator_profile(provider: str) -> ProviderProfile:
    for profile in DEFAULT_PROVIDER_REGISTRY.profiles:
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
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export provider-scoped browser cookies for Docker Runner",
    )
    parser.add_argument("--provider", required=True, choices=("youtube", "tiktok"))
    parser.add_argument(
        "--browser", default="chrome", choices=("chrome", "chromium", "firefox")
    )
    parser.add_argument("--profile")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    arguments = parser.parse_args()
    target, count = export_browser_cookies(
        provider=arguments.provider,
        browser=arguments.browser,
        profile=arguments.profile,
        version=arguments.version,
        output_root=arguments.output_root,
    )
    print(f"exported provider={arguments.provider} cookies={count} target={target}")


if __name__ == "__main__":
    main()
