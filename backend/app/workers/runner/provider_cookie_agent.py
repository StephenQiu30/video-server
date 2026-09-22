"""Manage the macOS provider Cookie synchronization agent."""

from __future__ import annotations

import argparse
import os
import plistlib
import stat
import subprocess
import sys
import time
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.provider_authorization import ProviderAuthorizationRequest
from app.services.provider_types import (
    ProviderAuthorizationSource,
    ProviderKey,
    ProviderSessionVersion,
)
from app.workers.runner._secure_file import atomic_write_bytes, ensure_private_directory
from app.workers.runner.provider_authorization_queue import (
    AUTHORIZATION_READY_MARKER,
    AUTHORIZATION_SOURCE_DIRECTORY,
    authorization_runtime,
    prepare_authorization_runtime,
    read_authorization_request,
    read_authorization_source,
    write_authorization_source,
)
from app.workers.runner.provider_browser_bridge import (
    browser_extension_id,
    install_native_host,
    uninstall_native_host,
)
from app.workers.runner.provider_browser_bridge_store import (
    ProviderBrowserBridgeStore,
)
from app.workers.runner.provider_cookie_boundary import (
    export_provider_cookie_lease_bounded,
)
from app.workers.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
    seal_cookie_lease,
)
from app.workers.runner.provider_cookie_process import termination_guard
from app.workers.runner.provider_cookie_queue import (
    AGENT_READY_MARKER,
    AGENT_READY_PAYLOAD,
    DEFAULT_ACK_TIMEOUT_SECONDS,
    ProviderCookieOperation,
    ProviderCookieRequest,
    drain_request_batch,
    prepare_runtime,
)
from app.workers.runner.provider_session_policy import (
    ProviderSessionSource,
    browser_session_policy,
    browser_session_providers,
)

SERVICE_ID = "com.framefetch.provider-cookie-agent"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_ID}.plist"
_MISSING_SERVICE = 113
_DIAGNOSTIC_FAILURE = 5
BROWSER_BRIDGE_HANDSHAKE_SECONDS = 15.0
DEFAULT_PROFILE = "Default"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RUNTIME_ROOT = (
    Path.home() / "Library" / "Caches" / "FrameFetch" / "provider-cookie-agent"
)
DEFAULT_BROWSER_ROOT = (
    Path.home()
    / "Library"
    / "Application Support"
    / "FrameFetch"
    / "provider-browser-sessions"
)
_AUTHORIZATION_URLS = {
    ProviderKey.YOUTUBE: "https://www.youtube.com/",
    ProviderKey.DOUYIN: "https://www.douyin.com/",
    ProviderKey.XIAOHONGSHU: "https://www.xiaohongshu.com/",
    ProviderKey.X: "https://x.com/",
    ProviderKey.INSTAGRAM: "https://www.instagram.com/",
    ProviderKey.FACEBOOK: "https://www.facebook.com/",
    ProviderKey.REDDIT: "https://www.reddit.com/",
    ProviderKey.PINTEREST: "https://www.pinterest.com/",
}


def install_agent(
    runtime_root: Path,
    *,
    profile: str,
    browser_root: Path | None = None,
) -> None:
    _require_macos()
    runtime_root = runtime_root.absolute()
    _stop_loaded_agent()
    runtime_root.mkdir(mode=0o711, parents=True, exist_ok=True)
    os.chmod(runtime_root, 0o711)
    if browser_root is not None:
        ensure_private_directory(browser_root.absolute())
    for provider in browser_session_providers():
        provider_root = _provider_runtime(runtime_root, provider)
        prepare_runtime(provider_root)
        _write_ready_marker(provider_root)
    authorization_root = authorization_runtime(runtime_root)
    prepare_authorization_runtime(runtime_root)
    ProviderBrowserBridgeStore(runtime_root).prepare()
    _write_ready_marker(authorization_root)
    _write_plist(
        PLIST_PATH,
        _launch_agent_plist(runtime_root, profile, browser_root=browser_root),
    )
    install_native_host(runtime_root, browser_extension_id())
    subprocess.run(("launchctl", "bootstrap", _domain(), str(PLIST_PATH)), check=True)
    print(f"installed: {PLIST_PATH}")


def uninstall_agent(runtime_root: Path) -> None:
    _require_macos()
    _stop_loaded_agent()
    PLIST_PATH.unlink(missing_ok=True)
    uninstall_native_host()
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
    authorization_root = authorization_runtime(runtime_root)
    (authorization_root / AUTHORIZATION_READY_MARKER).unlink(missing_ok=True)
    for name in (
        "requests",
        "responses",
        "cancelled",
        ".discarded",
        "",
    ):
        directory = authorization_root / name
        try:
            directory.rmdir()
        except OSError:
            pass
    source_root = runtime_root / AUTHORIZATION_SOURCE_DIRECTORY
    for source in source_root.glob("*.source") if source_root.exists() else ():
        _remove_authorization_entry(source)
    try:
        source_root.rmdir()
    except OSError:
        pass
    try:
        ProviderBrowserBridgeStore(runtime_root).clear()
    except FileNotFoundError:
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


def diagnose_sources(
    *,
    profile: str,
    provider: ProviderKey | None = None,
    browser_root: Path | None = None,
    source: ProviderAuthorizationSource = ProviderAuthorizationSource.DEDICATED_CHROME,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
) -> int:
    """Report bounded, non-secret source states for operator diagnostics."""
    providers = (
        (provider,)
        if provider is not None
        else tuple(sorted(browser_session_providers(), key=str))
    )
    if not providers:
        return 0

    def diagnose(item: ProviderKey) -> ProviderCookieLease:
        try:
            return _export_from_source(
                item,
                profile=profile,
                version=ProviderSessionVersion.BROWSER,
                browser_root=browser_root,
                source=source,
                runtime_root=runtime_root,
            )
        except Exception:
            return ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)

    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        futures = {item: pool.submit(diagnose, item) for item in providers}
        results = {item: futures[item].result() for item in providers}

    for item in providers:
        print(f"{item.value}: {results[item].status.value}")
    return (
        0
        if all(
            result.status is ProviderCookieLeaseStatus.OK for result in results.values()
        )
        else _DIAGNOSTIC_FAILURE
    )


def _launch_agent_plist(
    runtime_root: Path,
    profile: str,
    *,
    browser_root: Path | None = None,
) -> dict[str, Any]:
    arguments = [
        str(Path(sys.executable).absolute()),
        "-m",
        "app.workers.runner.provider_cookie_agent",
        "run",
        "--runtime-root",
        str(runtime_root),
        "--profile",
        profile,
    ]
    if browser_root is not None:
        arguments.extend(("--browser-root", str(browser_root.absolute())))
    return {
        "Label": SERVICE_ID,
        "ProgramArguments": arguments,
        "WorkingDirectory": str(PROJECT_ROOT / "backend"),
        "QueueDirectories": [
            str(_provider_runtime(runtime_root, provider) / "requests")
            for provider in sorted(browser_session_providers(), key=str)
        ]
        + [str(authorization_runtime(runtime_root) / "requests")],
        "ProcessType": "Background",
        # launchd defaults to 10 seconds, exceeding the runner's 2-second probe.
        "ThrottleInterval": 1,
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


def _write_plist(target: Path, document: dict[str, Any]) -> None:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.parent.is_symlink() or not stat.S_ISDIR(target.parent.lstat().st_mode):
        raise SystemExit("unsafe LaunchAgents directory")
    atomic_write_bytes(target, plistlib.dumps(document))


def _write_ready_marker(runtime_root: Path) -> None:
    marker = runtime_root / AGENT_READY_MARKER
    atomic_write_bytes(marker, AGENT_READY_PAYLOAD, mode=0o644)


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit("the provider Cookie agent requires macOS")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="帧取平台 Cookie 同步工具")
    parser.add_argument(
        "command",
        choices=("install", "status", "doctor", "uninstall", "run", "authorize"),
    )
    parser.add_argument("--runtime-root", type=Path, default=DEFAULT_RUNTIME_ROOT)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--provider", type=ProviderKey)
    parser.add_argument("--browser-root", type=Path, default=DEFAULT_BROWSER_ROOT)
    parser.add_argument(
        "--source",
        type=ProviderAuthorizationSource,
        default=ProviderAuthorizationSource.DEDICATED_CHROME,
    )
    parser.add_argument("--wait-seconds", type=float, default=600.0)
    return parser


def authorize_provider(
    provider: ProviderKey,
    *,
    browser_root: Path = DEFAULT_BROWSER_ROOT,
    profile: str = DEFAULT_PROFILE,
    wait_seconds: float = 600.0,
    source: ProviderAuthorizationSource = ProviderAuthorizationSource.DEDICATED_CHROME,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
) -> int:
    """Authorize from an explicit current or dedicated Chrome source."""
    _require_macos()
    if (
        browser_session_policy(provider).source
        is not ProviderSessionSource.CHROME_PROFILE
    ):
        raise SystemExit(
            f"{provider.value} uses a managed non-Chrome session and cannot be "
            "authorized by this agent"
        )
    if provider not in _AUTHORIZATION_URLS:
        raise SystemExit(f"{provider.value} has no local browser authorization flow")
    if wait_seconds <= 0:
        raise SystemExit("wait-seconds must be positive")
    if source is ProviderAuthorizationSource.DEDICATED_CHROME:
        provider_root = _chrome_root_for_source(
            provider,
            browser_root=browser_root,
            source=source,
        )
        subprocess.run(
            (
                "open",
                "-na",
                "Google Chrome",
                "--args",
                f"--user-data-dir={provider_root}",
                "--profile-directory=Default",
                _AUTHORIZATION_URLS[provider],
            ),
            check=True,
        )
        print(f"browser-opened: {provider.value}")
    else:
        print(f"checking-browser-bridge: {provider.value}")
    deadline = time.monotonic() + wait_seconds
    while True:
        result = _export_from_source(
            provider,
            profile=profile,
            version=ProviderSessionVersion.BROWSER,
            browser_root=browser_root,
            source=source,
            runtime_root=runtime_root,
        )
        if result.status is ProviderCookieLeaseStatus.OK:
            write_authorization_source(runtime_root, provider, source)
            print(f"authorized: {provider.value}")
            if source is ProviderAuthorizationSource.DEDICATED_CHROME:
                print(
                    "next: install the on-demand agent with "
                    f"--browser-root {browser_root.absolute()}"
                )
            return 0
        if time.monotonic() >= deadline:
            print(f"authorization-timeout: {provider.value}")
            return _DIAGNOSTIC_FAILURE
        time.sleep(2)


def drain_requests(
    runtime_root: Path,
    *,
    profile: str,
    browser_root: Path | None = None,
    acknowledgement_timeout_seconds: float = DEFAULT_ACK_TIMEOUT_SECONDS,
) -> None:
    def refresh(
        provider: ProviderKey, version: ProviderSessionVersion
    ) -> ProviderCookieLease:
        return _export_from_source(
            provider,
            profile=profile,
            version=version,
            browser_root=browser_root,
            source=read_authorization_source(runtime_root, provider)
            or ProviderAuthorizationSource.CURRENT_CHROME,
            runtime_root=runtime_root,
        )

    providers = sorted(browser_session_providers(), key=str)
    if not providers:
        return

    def drain(provider: ProviderKey, operation: ProviderCookieOperation) -> None:
        drain_request_batch(
            _provider_runtime(runtime_root, provider),
            provider,
            refresh,
            _write_response,
            acknowledgement_timeout_seconds=acknowledgement_timeout_seconds,
            operation=operation,
        )

    with (
        termination_guard(),
        ThreadPoolExecutor(max_workers=len(providers) + 1) as pool,
    ):
        authorization = pool.submit(
            drain_authorization_requests,
            runtime_root,
            profile=profile,
            browser_root=browser_root,
        )
        # One bounded export per provider; slow origins cannot starve later probes
        # or other origins. All child exports retain their existing timeout/cleanup.
        for provider in providers:
            drain(provider, ProviderCookieOperation.PROBE)
        pending = {
            provider: pool.submit(drain, provider, ProviderCookieOperation.REFRESH)
            for provider in providers
        }
        while pending or not authorization.done():
            wait(pending.values(), timeout=0.05)
            for provider in providers:
                drain(provider, ProviderCookieOperation.PROBE)
            completed = [
                provider for provider, future in pending.items() if future.done()
            ]
            for provider in completed:
                pending.pop(provider).result()
            if not pending and authorization.done():
                break
            for provider in completed:
                pending[provider] = pool.submit(
                    drain, provider, ProviderCookieOperation.REFRESH
                )
            # Keep exports in their provider slots while interactive authorization
            # waits too. A blocking export must never run on the probe loop.
            if authorization.done():
                continue
            time.sleep(0.05)
        authorization.result()


def drain_authorization_requests(
    runtime_root: Path,
    *,
    profile: str,
    browser_root: Path | None,
) -> None:
    """Handle current and newly-arriving intents without exposing Cookies."""

    requests, responses, cancelled = prepare_authorization_runtime(runtime_root)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures: dict[Future[None], str] = {}
        while True:
            active_tokens = frozenset(futures.values())
            for request in sorted(requests.glob("*.request")):
                token = request.name.removesuffix(".request")
                if token in active_tokens:
                    continue
                if len(token) != 32 or any(
                    character not in "0123456789abcdef" for character in token
                ):
                    _remove_authorization_entry(request)
                    continue
                try:
                    parsed = read_authorization_request(request)
                except (OSError, ValueError):
                    _remove_authorization_entry(request)
                    continue
                arguments = (
                    request,
                    token,
                    parsed,
                    responses,
                    cancelled,
                    runtime_root,
                    profile,
                    browser_root,
                )
                if parsed.probe:
                    # Probes never open a browser or read a session, so handle
                    # them immediately even while all interactive slots wait.
                    _authorize_request(*arguments)
                elif len(futures) < 4:
                    futures[pool.submit(_authorize_request, *arguments)] = token

            completed = [future for future in futures if future.done()]
            for future in completed:
                futures.pop(future)
                future.result()
            if futures:
                wait(tuple(futures), timeout=0.05)
                continue
            # A launchd queue event racing this final check will either be seen
            # here or start the on-demand job again after this process exits.
            if any(requests.glob("*.request")):
                continue
            return


def _authorize_request(
    request: Path,
    token: str,
    parsed: ProviderAuthorizationRequest,
    responses: Path,
    cancelled: Path,
    runtime_root: Path,
    profile: str,
    browser_root: Path | None,
) -> None:
    response = responses / f"{token}.response"
    cancel_marker = cancelled / f"{token}.cancel"
    bridge_deadline = datetime.now(UTC).timestamp() + BROWSER_BRIDGE_HANDSHAKE_SECONDS
    try:
        if cancel_marker.exists():
            return
        if datetime.now(UTC) >= parsed.expires_at:
            return
        if parsed.probe:
            _write_authorization_response(response, "agent_ready")
            return
        if parsed.source is ProviderAuthorizationSource.DEDICATED_CHROME:
            provider_root = _chrome_root_for_source(
                parsed.provider,
                browser_root=browser_root,
                source=parsed.source,
            )
            subprocess.run(
                (
                    "open",
                    "-na",
                    "Google Chrome",
                    "--args",
                    f"--user-data-dir={provider_root}",
                    "--profile-directory=Default",
                    _AUTHORIZATION_URLS[parsed.provider],
                ),
                check=True,
            )
        while datetime.now(UTC) < parsed.expires_at:
            if cancel_marker.exists():
                return
            lease = _export_from_source(
                parsed.provider,
                profile=profile,
                version=ProviderSessionVersion.BROWSER,
                browser_root=browser_root,
                source=parsed.source,
                runtime_root=runtime_root,
            )
            if lease.status is ProviderCookieLeaseStatus.OK:
                if cancel_marker.exists() or datetime.now(UTC) >= parsed.expires_at:
                    return
                write_authorization_source(
                    runtime_root,
                    provider=parsed.provider,
                    source=parsed.source,
                )
                _write_authorization_response(
                    response,
                    "source_available",
                )
                return
            if lease.status is ProviderCookieLeaseStatus.PERMISSION_DENIED:
                # A missing browser bridge or a macOS TCC denial is deterministic.
                # Give the browser connector a short handshake window, but do not
                # make the UI wait for the ten-minute transaction TTL.
                if (
                    parsed.source is ProviderAuthorizationSource.CURRENT_CHROME
                    and datetime.now(UTC).timestamp() < bridge_deadline
                ):
                    time.sleep(0.5)
                    continue
                _write_authorization_response(
                    response,
                    ProviderCookieLeaseStatus.PERMISSION_DENIED.value,
                )
                return
            time.sleep(2)
        _write_authorization_response(response, "credential_required")
    except Exception:
        _write_authorization_response(response, "provider_session_unavailable")
    finally:
        _remove_authorization_entry(request)
        # API terminal markers fence delayed queue publishers until the durable
        # result retention ends; the API cleanup owns their removal.
        if parsed.probe:
            _remove_authorization_entry(cancel_marker)


def _write_authorization_response(target: Path, value: str) -> None:
    atomic_write_bytes(target, f"{value}\n".encode("ascii"), mode=0o644)


def _remove_authorization_entry(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _provider_runtime(runtime_root: Path, provider: ProviderKey) -> Path:
    return runtime_root / provider.value


def _provider_browser_root(browser_root: Path, provider: ProviderKey) -> Path:
    root = browser_root.absolute()
    ensure_private_directory(root)
    provider_root = root / provider.value
    ensure_private_directory(provider_root)
    return provider_root


def _chrome_root_for_source(
    provider: ProviderKey,
    *,
    browser_root: Path | None,
    source: ProviderAuthorizationSource,
) -> Path | None:
    if (
        browser_session_policy(provider).source
        is not ProviderSessionSource.CHROME_PROFILE
    ):
        return None
    if source is ProviderAuthorizationSource.CURRENT_CHROME:
        return None
    if browser_root is None:
        return None
    return _provider_browser_root(browser_root or DEFAULT_BROWSER_ROOT, provider)


def _export_from_source(
    provider: ProviderKey,
    *,
    profile: str,
    version: ProviderSessionVersion,
    browser_root: Path | None,
    source: ProviderAuthorizationSource,
    runtime_root: Path = DEFAULT_RUNTIME_ROOT,
) -> ProviderCookieLease:
    policy = browser_session_policy(provider)
    if (
        source is ProviderAuthorizationSource.CURRENT_CHROME
        and policy.source is ProviderSessionSource.CHROME_PROFILE
    ):
        payload = ProviderBrowserBridgeStore(runtime_root).read(provider)
        if payload is None:
            return ProviderCookieLease(ProviderCookieLeaseStatus.PERMISSION_DENIED)
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, payload)
    chrome_root = _chrome_root_for_source(
        provider,
        browser_root=browser_root,
        source=source,
    )
    if chrome_root is None:
        return export_provider_cookie_lease_bounded(
            provider=provider,
            profile=profile,
            version=version,
        )
    return export_provider_cookie_lease_bounded(
        provider=provider,
        profile=profile,
        version=version,
        chrome_root=chrome_root,
    )


def _browser_root_or_none(
    browser_root: Path | None, provider: ProviderKey
) -> Path | None:
    if browser_root is None or (
        browser_session_policy(provider).source
        is not ProviderSessionSource.CHROME_PROFILE
    ):
        return None
    return _provider_browser_root(browser_root, provider)


def _write_response(
    target: Path,
    request: ProviderCookieRequest,
    lease: ProviderCookieLease,
) -> None:
    result = seal_cookie_lease(
        lease,
        request.public_key,
        associated_data=request.serialize(),
    )
    atomic_write_bytes(target, result, mode=0o644)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _require_macos()
    if args.command == "install":
        install_agent(
            args.runtime_root,
            profile=args.profile,
            browser_root=args.browser_root,
        )
    elif args.command == "uninstall":
        uninstall_agent(args.runtime_root)
    elif args.command == "status":
        return agent_status()
    elif args.command == "doctor":
        return diagnose_sources(
            profile=args.profile,
            provider=args.provider,
            browser_root=args.browser_root,
            source=args.source,
            runtime_root=args.runtime_root,
        )
    elif args.command == "authorize":
        if args.provider is None:
            raise SystemExit("authorize requires --provider")
        return authorize_provider(
            args.provider,
            browser_root=args.browser_root or DEFAULT_BROWSER_ROOT,
            profile=args.profile,
            wait_seconds=args.wait_seconds,
            source=args.source,
            runtime_root=args.runtime_root,
        )
    else:
        drain_requests(
            args.runtime_root,
            profile=args.profile,
            browser_root=args.browser_root,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
