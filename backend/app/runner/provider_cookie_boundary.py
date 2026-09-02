"""Run provider-scoped Chrome Cookie export in a bounded child process."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from typing import Final

from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.provider_cookie_export import export_provider_cookie_lease
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
    parse_export,
    serialize_export,
)
from app.runner.provider_cookie_process import (
    defer_termination,
    process_group_exists,
    terminate_process_group,
    terminate_safely,
    termination_guard,
    unblock_termination_signals,
)

DEFAULT_TIMEOUT_SECONDS: Final = 15.0
DEFAULT_TERMINATE_GRACE_SECONDS: Final = 0.25
_MODULE: Final = "app.runner.provider_cookie_boundary"


def export_provider_cookie_lease_bounded(
    *,
    provider: ProviderKey,
    profile: str,
    version: ProviderSessionVersion,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    terminate_grace_seconds: float = DEFAULT_TERMINATE_GRACE_SECONDS,
) -> ProviderCookieLease:
    """Extract through a short-lived process and retain the payload only in memory."""
    if timeout_seconds <= 0 or terminate_grace_seconds <= 0:
        return ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)
    process: subprocess.Popen[bytes] | None = None
    with termination_guard():
        try:
            with defer_termination():
                process = subprocess.Popen(
                    _child_command(
                        provider,
                        profile,
                        version,
                    ),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            stdout, _ = process.communicate(timeout=timeout_seconds)
            if process_group_exists(process.pid):
                terminate_process_group(process, terminate_grace_seconds)
                return ProviderCookieLease(
                    ProviderCookieLeaseStatus.SESSION_UNAVAILABLE
                )
            if process.returncode != 0:
                return ProviderCookieLease(
                    ProviderCookieLeaseStatus.SESSION_UNAVAILABLE
                )
            return parse_export(stdout)
        except subprocess.TimeoutExpired:
            if process is not None:
                terminate_safely(process, terminate_grace_seconds)
            return ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)
        except Exception:
            if process is not None:
                terminate_safely(process, terminate_grace_seconds)
            return ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)
        except BaseException:
            if process is not None:
                terminate_safely(process, terminate_grace_seconds)
            raise


def _child_command(
    provider: ProviderKey,
    profile: str,
    version: ProviderSessionVersion,
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        _MODULE,
        "child",
        "--provider",
        provider.value,
        "--profile",
        profile,
        "--version",
        version.value,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", choices=("child",))
    parser.add_argument("--provider", type=ProviderKey, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--version", type=ProviderSessionVersion, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with termination_guard():
        unblock_termination_signals()
        try:
            result = export_provider_cookie_lease(
                provider=args.provider,
                profile=args.profile,
                version=args.version,
            )
        except Exception:
            result = ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)
    sys.stdout.buffer.write(serialize_export(result))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
