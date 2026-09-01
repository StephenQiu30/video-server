"""Manage the on-demand macOS Chrome Cookie synchronization agent."""

from __future__ import annotations

import argparse
import os
import plistlib
import stat
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import Any

from app.runner.youtube_cookie_boundary import sync_cookie_file_bounded
from app.runner.youtube_cookie_queue import AGENT_READY_MARKER
from app.runner.youtube_cookie_sync import (
    DEFAULT_PROFILE,
    DEFAULT_RUNTIME_ROOT,
    DEFAULT_SECRET_ROOT,
    DEFAULT_VERSION,
    PROJECT_ROOT,
    drain_requests,
    prepare_runtime,
    prepare_secret_root,
)

SERVICE_ID = "com.framefetch.youtube-cookie-sync"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_ID}.plist"
_MISSING_SERVICE = 113


def install_agent(
    runtime_root: Path,
    secret_root: Path,
    *,
    profile: str,
    version: str,
) -> None:
    _require_macos()
    runtime_root = runtime_root.absolute()
    secret_root = secret_root.absolute()
    prepare_runtime(runtime_root)
    prepare_secret_root(secret_root)
    _stop_loaded_agent()
    _atomic_write_plist(
        PLIST_PATH,
        _launch_agent_plist(runtime_root, secret_root, profile, version),
    )
    subprocess.run(("launchctl", "bootstrap", _domain(), str(PLIST_PATH)), check=True)
    _write_ready_marker(runtime_root)
    print(f"installed: {PLIST_PATH}")


def uninstall_agent(runtime_root: Path) -> None:
    _require_macos()
    _stop_loaded_agent()
    PLIST_PATH.unlink(missing_ok=True)
    runtime_root = runtime_root.absolute()
    (runtime_root / AGENT_READY_MARKER).unlink(missing_ok=True)
    for name in ("requests", "responses", ".discarded", ""):
        directory = runtime_root / name
        try:
            directory.rmdir()
        except OSError:
            pass
    print("uninstalled")


def agent_status() -> int:
    _require_macos()
    result = _launchctl_print()
    if result.returncode == 0:
        print("installed: waiting on demand")
        return 0
    if result.returncode == _MISSING_SERVICE:
        print("not installed")
        return 4
    print("status unavailable")
    return result.returncode


def _launch_agent_plist(
    runtime_root: Path,
    secret_root: Path,
    profile: str,
    version: str,
) -> dict[str, Any]:
    return {
        "Label": SERVICE_ID,
        "ProgramArguments": [
            str(Path(sys.executable).absolute()),
            "-m",
            "app.runner.youtube_cookie_agent",
            "run",
            "--runtime-root",
            str(runtime_root),
            "--secret-root",
            str(secret_root),
            "--profile",
            profile,
            "--version",
            version,
        ],
        "WorkingDirectory": str(PROJECT_ROOT / "backend"),
        "QueueDirectories": [str(runtime_root / "requests")],
        "ProcessType": "Background",
        "Umask": 0o077,
        "EnvironmentVariables": {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin"
        },
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": "/dev/null",
    }


def _stop_loaded_agent() -> bool:
    result = _launchctl_print()
    if result.returncode == _MISSING_SERVICE:
        return False
    if result.returncode != 0:
        raise SystemExit("unable to inspect the YouTube Cookie agent")
    subprocess.run(("launchctl", "bootout", f"{_domain()}/{SERVICE_ID}"), check=True)
    return True


def _launchctl_print() -> subprocess.CompletedProcess[str]:
    command = ("launchctl", "print", f"{_domain()}/{SERVICE_ID}")
    return subprocess.run(command, check=False, capture_output=True, text=True)


def _atomic_write_plist(target: Path, document: dict[str, Any]) -> None:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.parent.is_symlink() or not stat.S_ISDIR(target.parent.lstat().st_mode):
        raise SystemExit("unsafe LaunchAgents directory")
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            output.write(plistlib.dumps(document))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def _write_ready_marker(runtime_root: Path) -> None:
    marker = runtime_root / AGENT_READY_MARKER
    descriptor, raw_temp = tempfile.mkstemp(prefix=f".{marker.name}.", dir=runtime_root)
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "w", encoding="ascii", closefd=True) as output:
            output.write("installed\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, marker)
    finally:
        temp.unlink(missing_ok=True)


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit("the YouTube Cookie agent requires macOS")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="帧取 YouTube Cookie 同步工具")
    parser.add_argument("command", choices=("install", "status", "uninstall", "run"))
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--secret-root", type=Path, default=DEFAULT_SECRET_ROOT)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _require_macos()
    if args.command == "install":
        install_agent(
            args.runtime_root,
            args.secret_root,
            profile=args.profile,
            version=args.version,
        )
    elif args.command == "uninstall":
        uninstall_agent(args.runtime_root)
    elif args.command == "status":
        return agent_status()
    else:
        drain_requests(
            args.runtime_root,
            args.secret_root,
            profile=args.profile,
            version=args.version,
            refresh=partial(
                sync_cookie_file_bounded,
                args.secret_root,
                profile=args.profile,
                version=args.version,
            ),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
