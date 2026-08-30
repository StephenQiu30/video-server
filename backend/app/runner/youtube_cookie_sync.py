"""Synchronize a minimal YouTube Cookie jar from the local Chrome profile."""

from __future__ import annotations

import os
import re
import tempfile
import time
from collections.abc import Callable
from http.cookiejar import Cookie
from pathlib import Path
from typing import Final, Literal

from app.runner.chrome_youtube_cookies import extract_youtube_cookies
from app.runner.youtube_cookie_process import termination_guard
from app.runner.youtube_cookie_queue import (
    DEFAULT_ACK_TIMEOUT_SECONDS,
    drain_request_batch,
)
from app.runner.youtube_cookie_queue import (
    prepare_runtime as prepare_runtime,
)
from app.runner.youtube_cookie_staging import (
    prepare_secret_root as prepare_secret_root,
)
from app.runner.youtube_cookie_staging import publish_cookie_payload

SyncResult = Literal["ok", "credential_required", "provider_session_unavailable"]

OK: Final[SyncResult] = "ok"
CREDENTIAL_REQUIRED: Final[SyncResult] = "credential_required"
SESSION_UNAVAILABLE: Final[SyncResult] = "provider_session_unavailable"
DEFAULT_PROFILE = "Default"
DEFAULT_VERSION = "chrome-default-v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_ROOT = (
    Path.home() / "Library" / "Caches" / "FrameFetch" / "youtube-cookie-sync"
)
DEFAULT_SECRET_ROOT = PROJECT_ROOT / ".provider-secrets" / "youtube"

_ALLOWED_DOMAINS = ("youtube.com", "youtube-nocookie.com")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_CONTROL = frozenset("\t\r\n")
_MAX_COOKIE_BYTES = 1024**2


def sync_cookie_file(
    secret_root: Path = DEFAULT_SECRET_ROOT,
    *,
    profile: str = DEFAULT_PROFILE,
    version: str = DEFAULT_VERSION,
    clock: Callable[[], float] = time.time,
    staging: Path | None = None,
) -> SyncResult:
    """Refresh one allowlisted Cookie file without exposing browser data."""
    if _VERSION.fullmatch(version) is None:
        return SESSION_UNAVAILABLE
    try:
        jar = extract_youtube_cookies(profile)
        now = int(clock())
        cookies = tuple(cookie for cookie in jar if _eligible(cookie, now))
        if not cookies:
            return CREDENTIAL_REQUIRED
        prepare_secret_root(secret_root)
        payload = _cookie_payload(cookies)
        publish_cookie_payload(secret_root, version, payload, staging)
    except FileNotFoundError:
        return CREDENTIAL_REQUIRED
    except Exception:
        return SESSION_UNAVAILABLE
    return OK


def drain_requests(
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
    secret_root: Path = DEFAULT_SECRET_ROOT,
    *,
    profile: str = DEFAULT_PROFILE,
    version: str = DEFAULT_VERSION,
    refresh: Callable[[], SyncResult] | None = None,
    acknowledgement_timeout_seconds: float = DEFAULT_ACK_TIMEOUT_SECONDS,
) -> None:
    """Serve one queued batch, wait for clients to consume it, and exit."""
    update = refresh or (
        lambda: sync_cookie_file(secret_root, profile=profile, version=version)
    )
    with termination_guard():
        drain_request_batch(
            runtime_root,
            update,
            _atomic_write_response,
            acknowledgement_timeout_seconds=acknowledgement_timeout_seconds,
        )


def _eligible(cookie: Cookie, now: int) -> bool:
    domain = cookie.domain.lstrip(".").casefold()
    allowed = any(
        domain == item or domain.endswith(f".{item}") for item in _ALLOWED_DOMAINS
    )
    fields = (cookie.domain, cookie.path, cookie.name, cookie.value or "")
    return (
        allowed
        and not cookie.is_expired(now)
        and cookie.path.startswith("/")
        and all(not (_CONTROL & set(field)) for field in fields)
    )


def _cookie_payload(cookies: tuple[Cookie, ...]) -> bytes:
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookies:
        name, value = cookie.name, cookie.value
        if value is None:
            name, value = "", name
        domain = cookie.domain
        if cookie.has_nonstandard_attr("HttpOnly"):
            domain = f"#HttpOnly_{domain}"
        lines.append(
            "\t".join(
                (
                    domain,
                    "TRUE" if cookie.domain.startswith(".") else "FALSE",
                    cookie.path,
                    "TRUE" if cookie.secure else "FALSE",
                    str(cookie.expires or 0),
                    name,
                    value,
                )
            )
        )
    payload = ("\n".join(lines) + "\n").encode()
    if len(payload) > _MAX_COOKIE_BYTES:
        raise OSError("Cookie payload exceeds the bounded session file size")
    return payload


def _atomic_write_response(target: Path, result: str) -> None:
    _atomic_write(target, result.encode("ascii"), mode=0o644)


def _atomic_write(target: Path, payload: bytes, *, mode: int = 0o600) -> None:
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, target)
        _fsync_directory(target.parent)
    finally:
        temp.unlink(missing_ok=True)


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
