"""Run host Chrome Cookie extraction behind a bounded process boundary."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from app.runner.youtube_cookie_process import (
    defer_termination,
    process_group_exists,
    terminate_process_group,
    terminate_safely,
    termination_guard,
    unblock_termination_signals,
)
from app.runner.youtube_cookie_staging import create_cookie_staging
from app.runner.youtube_cookie_sync import (
    CREDENTIAL_REQUIRED,
    DEFAULT_PROFILE,
    DEFAULT_SECRET_ROOT,
    DEFAULT_VERSION,
    OK,
    SESSION_UNAVAILABLE,
    SyncResult,
    sync_cookie_file,
)

DEFAULT_TIMEOUT_SECONDS: Final = 15.0
DEFAULT_TERMINATE_GRACE_SECONDS: Final = 0.25
_MODULE: Final = "app.runner.youtube_cookie_boundary"
_RESULTS: Final = frozenset((OK, CREDENTIAL_REQUIRED, SESSION_UNAVAILABLE))


def sync_cookie_file_bounded(
    secret_root: Path = DEFAULT_SECRET_ROOT,
    *,
    profile: str = DEFAULT_PROFILE,
    version: str = DEFAULT_VERSION,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    terminate_grace_seconds: float = DEFAULT_TERMINATE_GRACE_SECONDS,
) -> SyncResult:
    """Extract through a short-lived process and return only a stable status."""
    if timeout_seconds <= 0 or terminate_grace_seconds <= 0:
        return SESSION_UNAVAILABLE
    process: subprocess.Popen[bytes] | None = None
    staging: Path | None = None
    try:
        with termination_guard():
            try:
                with defer_termination():
                    staging = create_cookie_staging(secret_root, version)
                with defer_termination():
                    process = subprocess.Popen(
                        _child_command(secret_root, profile, version, staging),
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                stdout, _ = process.communicate(timeout=timeout_seconds)
                if process_group_exists(process.pid):
                    terminate_process_group(process, terminate_grace_seconds)
                    return SESSION_UNAVAILABLE
                if process.returncode != 0:
                    return SESSION_UNAVAILABLE
                result = stdout.decode("ascii")
            except subprocess.TimeoutExpired:
                if process is not None:
                    terminate_safely(process, terminate_grace_seconds)
                return SESSION_UNAVAILABLE
            except Exception:
                if process is not None:
                    terminate_safely(process, terminate_grace_seconds)
                return SESSION_UNAVAILABLE
            except BaseException:
                if process is not None:
                    terminate_safely(process, terminate_grace_seconds)
                raise
            if result not in _RESULTS:
                return SESSION_UNAVAILABLE
            return result
    finally:
        if staging is not None:
            with defer_termination():
                staging.unlink(missing_ok=True)


def _child_command(
    secret_root: Path,
    profile: str,
    version: str,
    staging: Path,
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        _MODULE,
        "child",
        "--secret-root",
        str(secret_root),
        "--profile",
        profile,
        "--version",
        version,
        "--staging",
        str(staging),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", choices=("child",))
    parser.add_argument("--secret-root", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--staging", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    with termination_guard():
        unblock_termination_signals()
        try:
            result = sync_cookie_file(
                args.secret_root,
                profile=args.profile,
                version=args.version,
                staging=args.staging,
            )
        except Exception:
            result = SESSION_UNAVAILABLE
    sys.stdout.write(result)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
