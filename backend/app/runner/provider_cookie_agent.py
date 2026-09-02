"""Manage the macOS provider Cookie synchronization agent."""

from __future__ import annotations

import argparse
import os
import plistlib
import stat
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.provider_cookie_boundary import export_provider_cookie_lease_bounded
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    seal_cookie_lease,
)
from app.runner.provider_cookie_process import termination_guard
from app.runner.provider_cookie_queue import (
    AGENT_READY_MARKER,
    AGENT_READY_PAYLOAD,
    DEFAULT_ACK_TIMEOUT_SECONDS,
    ProviderCookieRequest,
    drain_request_batch,
    prepare_runtime,
)
from app.runner.provider_session_policy import browser_session_providers

SERVICE_ID = "com.framefetch.provider-cookie-agent"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_ID}.plist"
_MISSING_SERVICE = 113
DEFAULT_PROFILE = "Default"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_ROOT = (
    Path.home() / "Library" / "Caches" / "FrameFetch" / "provider-cookie-agent"
)


def install_agent(
    runtime_root: Path,
    *,
    profile: str,
) -> None:
    _require_macos()
    runtime_root = runtime_root.absolute()
    _stop_loaded_agent()
    runtime_root.mkdir(mode=0o711, parents=True, exist_ok=True)
    os.chmod(runtime_root, 0o711)
    for provider in browser_session_providers():
        provider_root = _provider_runtime(runtime_root, provider)
        prepare_runtime(provider_root)
        _write_ready_marker(provider_root)
    _atomic_write_plist(
        PLIST_PATH,
        _launch_agent_plist(runtime_root, profile),
    )
    subprocess.run(("launchctl", "bootstrap", _domain(), str(PLIST_PATH)), check=True)
    print(f"installed: {PLIST_PATH}")


def uninstall_agent(runtime_root: Path) -> None:
    _require_macos()
    _stop_loaded_agent()
    PLIST_PATH.unlink(missing_ok=True)
    runtime_root = runtime_root.absolute()
    for provider in browser_session_providers():
        provider_root = _provider_runtime(runtime_root, provider)
        (provider_root / AGENT_READY_MARKER).unlink(missing_ok=True)
        for name in ("requests", "responses", ".discarded", ""):
            directory = provider_root / name
            try:
                directory.rmdir()
            except OSError:
                pass
    try:
        runtime_root.rmdir()
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
    profile: str,
) -> dict[str, Any]:
    return {
        "Label": SERVICE_ID,
        "ProgramArguments": [
            str(Path(sys.executable).absolute()),
            "-m",
            "app.runner.provider_cookie_agent",
            "run",
            "--runtime-root",
            str(runtime_root),
            "--profile",
            profile,
        ],
        "WorkingDirectory": str(PROJECT_ROOT / "backend"),
        "QueueDirectories": [
            str(_provider_runtime(runtime_root, provider) / "requests")
            for provider in sorted(browser_session_providers(), key=str)
        ],
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
        raise SystemExit("unable to inspect the provider Cookie agent")
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
            output.write(AGENT_READY_PAYLOAD.decode("ascii"))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, marker)
    finally:
        temp.unlink(missing_ok=True)


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit("the provider Cookie agent requires macOS")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="帧取平台 Cookie 同步工具")
    parser.add_argument("command", choices=("install", "status", "uninstall", "run"))
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    return parser


def drain_requests(
    runtime_root: Path,
    *,
    profile: str,
    acknowledgement_timeout_seconds: float = DEFAULT_ACK_TIMEOUT_SECONDS,
) -> None:
    def refresh(
        provider: ProviderKey, version: ProviderSessionVersion
    ) -> ProviderCookieLease:
        return export_provider_cookie_lease_bounded(
            provider=provider,
            profile=profile,
            version=version,
        )

    with termination_guard():
        for provider in sorted(browser_session_providers(), key=str):
            drain_request_batch(
                _provider_runtime(runtime_root, provider),
                provider,
                refresh,
                _atomic_write_response,
                acknowledgement_timeout_seconds=acknowledgement_timeout_seconds,
            )


def _provider_runtime(runtime_root: Path, provider: ProviderKey) -> Path:
    return runtime_root / provider.value


def _atomic_write_response(
    target: Path,
    request: ProviderCookieRequest,
    lease: ProviderCookieLease,
) -> None:
    result = seal_cookie_lease(
        lease,
        request.public_key,
        associated_data=request.serialize(),
    )
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            output.write(result)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _require_macos()
    if args.command == "install":
        install_agent(
            args.runtime_root,
            profile=args.profile,
        )
    elif args.command == "uninstall":
        uninstall_agent(args.runtime_root)
    elif args.command == "status":
        return agent_status()
    else:
        drain_requests(
            args.runtime_root,
            profile=args.profile,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
