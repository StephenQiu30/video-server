"""Continuously publish and report one provider-scoped browser session."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .browser_cookie_export import (
    BrowserLoginRequiredError,
    CookieLoader,
    export_browser_cookies,
    supported_browser_session_providers,
)
from .managed_chrome_session import ManagedChromeCookieLoader

type Reporter = Callable[[str], None]
type Sleeper = Callable[[float], None]


@dataclass(frozen=True, slots=True)
class BrokerStatus:
    provider: str
    version: str
    state: str
    updated_at: str
    secret_ready: bool


def run_session_broker(
    *,
    provider: str,
    browser: str,
    profile: str | None,
    version: str,
    output_root: Path,
    status_path: Path,
    interval_seconds: float,
    cookie_loader: CookieLoader | None = None,
    reporter: Reporter = lambda message: print(message, flush=True),
    sleeper: Sleeper = time.sleep,
    max_cycles: int | None = None,
) -> None:
    if interval_seconds < 5:
        raise ValueError("broker interval must be at least 5 seconds")
    if max_cycles is not None and max_cycles < 1:
        raise ValueError("max cycles must be positive")
    target = output_root.expanduser() / provider / f"{version}.cookies.txt"
    previous_digest = _file_digest(target)
    previous_state: str | None = None
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
            _write_status(status_path, provider, version, "ready", secret_ready=True)
            previous_state = "ready"
        except BrowserLoginRequiredError:
            if previous_state != "login_required":
                reporter(f"login_required provider={provider}")
            _write_status(
                status_path,
                provider,
                version,
                "login_required",
                secret_ready=target.exists(),
            )
            previous_state = "login_required"
        except (OSError, ValueError) as exc:
            if previous_state != "degraded":
                reporter(
                    f"refresh_failed provider={provider} reason={type(exc).__name__}"
                )
            _write_status(
                status_path,
                provider,
                version,
                "degraded",
                secret_ready=target.exists(),
            )
            previous_state = "degraded"
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            return
        sleeper(interval_seconds)


def _write_status(
    path: Path,
    provider: str,
    version: str,
    state: str,
    *,
    secret_ready: bool,
) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    status = BrokerStatus(
        provider=provider,
        version=version,
        state=state,
        updated_at=datetime.now(UTC).isoformat(),
        secret_ready=secret_ready,
    )
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(asdict(status), stream, separators=(",", ":"))
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _file_digest(path: Path) -> bytes | None:
    try:
        return hashlib.sha256(path.read_bytes()).digest()
    except FileNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a provider session broker")
    parser.add_argument(
        "--provider", required=True, choices=supported_browser_session_providers()
    )
    parser.add_argument(
        "--browser", default="chrome", choices=("chrome", "chromium", "firefox")
    )
    parser.add_argument("--profile")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--status-path", required=True, type=Path)
    parser.add_argument("--interval-seconds", type=float, default=15)
    arguments = parser.parse_args()
    managed_browser = (
        ManagedChromeCookieLoader(arguments.status_path.parent)
        if arguments.provider == "wechat_channels"
        and arguments.browser == "chrome"
        and arguments.profile is None
        else None
    )
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        run_session_broker(
            provider=arguments.provider,
            browser=arguments.browser,
            profile=arguments.profile,
            version=arguments.version,
            output_root=arguments.output_root,
            status_path=arguments.status_path,
            interval_seconds=arguments.interval_seconds,
            cookie_loader=managed_browser,
        )
    finally:
        if managed_browser is not None:
            managed_browser.close()


def _stop(_signum: int, _frame: object) -> None:
    raise SystemExit


if __name__ == "__main__":
    main()
