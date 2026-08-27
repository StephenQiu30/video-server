"""Export a browser session into a provider-scoped Docker secret."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import tempfile
import time
from collections.abc import Callable, Iterable
from http.cookiejar import Cookie, CookieJar, MozillaCookieJar
from pathlib import Path
from typing import cast

from yt_dlp import YoutubeDL  # type: ignore[import-untyped]

from app.domain.providers import ProviderAccessMode
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
}
type CookieLoader = Callable[[str, str | None], CookieJar]
type Reporter = Callable[[str], None]
type Sleeper = Callable[[float], None]


def _print_report(message: str) -> None:
    print(message, flush=True)


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


def watch_browser_cookies(
    *,
    provider: str,
    browser: str,
    profile: str | None,
    version: str,
    output_root: Path,
    interval_seconds: float,
    cookie_loader: CookieLoader | None = None,
    reporter: Reporter = _print_report,
    sleeper: Sleeper = time.sleep,
    max_cycles: int | None = None,
) -> None:
    """Keep a provider-scoped Docker secret aligned with a host browser session."""

    if interval_seconds < 5:
        raise ValueError("watch interval must be at least 5 seconds")
    if max_cycles is not None and max_cycles < 1:
        raise ValueError("max cycles must be positive")
    target = output_root.expanduser() / provider / f"{version}.cookies.txt"
    previous_digest = _file_digest(target)
    cycles = 0
    while True:
        try:
            refreshed, count = export_browser_cookies(
                provider=provider,
                browser=browser,
                profile=profile,
                version=version,
                output_root=output_root,
                cookie_loader=cookie_loader,
            )
            current_digest = _file_digest(refreshed)
            if current_digest != previous_digest:
                reporter(
                    f"refreshed provider={provider} cookies={count} version={version}"
                )
            previous_digest = current_digest
        except (OSError, ValueError) as exc:
            # Keep the last known-good file in place. Never include browser
            # paths, cookie values, or the underlying exception message in the
            # long-running bridge log.
            reporter(f"refresh_failed provider={provider} reason={type(exc).__name__}")
            if previous_digest is None:
                raise
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            return
        sleeper(interval_seconds)


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


def _file_digest(path: Path) -> bytes | None:
    try:
        return hashlib.sha256(path.read_bytes()).digest()
    except FileNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export provider-scoped browser cookies for Docker Runner",
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=tuple(sorted(_AUTH_COOKIE_NAMES)),
    )
    parser.add_argument(
        "--browser", default="chrome", choices=("chrome", "chromium", "firefox")
    )
    parser.add_argument("--profile")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--watch-interval-seconds",
        type=float,
        help=(
            "Continuously refresh the provider-scoped secret from the current "
            "browser login. Intended for a trusted local development host."
        ),
    )
    arguments = parser.parse_args()
    if arguments.watch_interval_seconds is not None:
        watch_browser_cookies(
            provider=arguments.provider,
            browser=arguments.browser,
            profile=arguments.profile,
            version=arguments.version,
            output_root=arguments.output_root,
            interval_seconds=arguments.watch_interval_seconds,
        )
        return
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
