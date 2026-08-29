"""Authorize one provider session without keeping a browser running."""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path

from app.runner.browser_cookie_export import (
    BrowserLoginRequiredError,
    CookieLoader,
    export_browser_cookies,
    supported_browser_session_providers,
)
from app.runner.managed_chrome_session import ManagedChromeCookieLoader

type Reporter = Callable[[str], None]
type Sleeper = Callable[[float], None]


def authorize_provider(
    *,
    provider: str,
    version: str,
    output_root: Path,
    cookie_loader: CookieLoader | None = None,
    wait_for_login: bool = False,
    reporter: Reporter = lambda message: print(message, flush=True),
    sleeper: Sleeper = time.sleep,
) -> Path:
    waiting_reported = False
    while True:
        try:
            target, _count = export_browser_cookies(
                provider=provider,
                browser="chrome",
                profile=None,
                version=version,
                output_root=output_root,
                cookie_loader=cookie_loader,
            )
        except BrowserLoginRequiredError:
            if not wait_for_login:
                raise
            if not waiting_reported:
                reporter(f"waiting_for_login provider={provider}")
                waiting_reported = True
            sleeper(2)
            continue
        reporter(f"authorized provider={provider} version={version}")
        return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authorize one provider session without a background broker"
    )
    parser.add_argument(
        "--provider", required=True, choices=supported_browser_session_providers()
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--state-root", required=True, type=Path)
    arguments = parser.parse_args()
    loader = (
        ManagedChromeCookieLoader(arguments.state_root)
        if arguments.provider == "wechat_channels"
        else None
    )
    try:
        authorize_provider(
            provider=arguments.provider,
            version=arguments.version,
            output_root=arguments.output_root,
            cookie_loader=loader,
            wait_for_login=loader is not None,
        )
    except BrowserLoginRequiredError:
        parser.exit(1, f"{arguments.provider} login is required\n")
    finally:
        if loader is not None:
            loader.close()


if __name__ == "__main__":
    main()
