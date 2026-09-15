"""Maintain one deployment-owned YouTube Cookie file outside user requests."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import FrameType

from app.domain.providers import ProviderKey
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_boundary import export_provider_cookie_lease_bounded
from app.runner.provider_cookie_file import ProviderCookieFile
from app.runner.provider_cookie_lease import ProviderCookieLeaseStatus
from app.runner.provider_session_policy import browser_session_policy
from app.runner.provider_session_setup import publish_session

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / ".provider-sessions" / "youtube"
DEFAULT_STATE_ROOT = (
    Path.home() / "Library" / "Caches" / "FrameFetch" / "youtube-session-maintainer"
)
DEFAULT_PROFILE = "Default"
DEFAULT_INTERVAL_SECONDS = 60


class MaintenanceResult(StrEnum):
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    BUSY = "busy"
    CREDENTIAL_REQUIRED = ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED.value
    SOURCE_MISSING = ProviderCookieLeaseStatus.SOURCE_MISSING.value
    PERMISSION_DENIED = ProviderCookieLeaseStatus.PERMISSION_DENIED.value
    SESSION_UNAVAILABLE = ProviderCookieLeaseStatus.SESSION_UNAVAILABLE.value


def refresh_youtube_source(
    source_root: Path,
    *,
    state_root: Path = DEFAULT_STATE_ROOT,
    profile: str = DEFAULT_PROFILE,
) -> MaintenanceResult:
    """Capture, validate and atomically publish a changed YouTube source."""
    source_root = source_root.absolute()
    state_root = state_root.absolute()
    _ensure_private_directory(state_root)
    lock = os.open(
        state_root / ".maintain.lock",
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        _validate_private_file(lock, "unsafe maintainer lock")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return MaintenanceResult.BUSY
        result = export_provider_cookie_lease_bounded(
            provider=ProviderKey.YOUTUBE,
            profile=profile,
            version=browser_session_policy(ProviderKey.YOUTUBE).version,
        )
        attempted_at = _timestamp()
        if result.status is not ProviderCookieLeaseStatus.OK or result.payload is None:
            outcome = MaintenanceResult(result.status.value)
            _write_state(
                state_root,
                status=outcome,
                attempted_at=attempted_at,
                revision=_current_revision(source_root),
            )
            return outcome

        payload = result.payload
        revision = hashlib.sha256(payload).hexdigest()
        if _current_payload(source_root) == payload:
            outcome = MaintenanceResult.UNCHANGED
        else:
            try:
                publish_session(ProviderKey.YOUTUBE, source_root, payload)
            except (OSError, RunnerFailure):
                outcome = MaintenanceResult.SESSION_UNAVAILABLE
                _write_state(
                    state_root,
                    status=outcome,
                    attempted_at=attempted_at,
                    revision=_current_revision(source_root),
                )
                return outcome
            outcome = MaintenanceResult.UPDATED
        _write_state(
            state_root,
            status=outcome,
            attempted_at=attempted_at,
            succeeded_at=attempted_at,
            revision=revision,
        )
        return outcome
    finally:
        os.close(lock)


def start_maintainer(
    source_root: Path,
    *,
    state_root: Path = DEFAULT_STATE_ROOT,
    profile: str = DEFAULT_PROFILE,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> None:
    """Start from an already authorized desktop host and detach from the project."""
    _require_macos()
    source_root = source_root.absolute()
    state_root = state_root.absolute()
    _ensure_private_directory(source_root)
    _ensure_private_directory(state_root)
    if _daemon_running(state_root):
        print("running: YouTube session maintenance already enabled")
        return

    initial = refresh_youtube_source(
        source_root, state_root=state_root, profile=profile
    )
    if initial not in {MaintenanceResult.UPDATED, MaintenanceResult.UNCHANGED}:
        raise SystemExit(f"YouTube session maintenance not started: {initial.value}")

    command = (
        str(Path(sys.executable).absolute()),
        "-m",
        "app.runner.provider_session_maintainer",
        "serve",
        "--directory",
        str(source_root),
        "--state-root",
        str(state_root),
        "--profile",
        profile,
        "--interval-seconds",
        str(interval_seconds),
    )
    with (
        open(os.devnull, "rb") as input_stream,
        open(os.devnull, "ab") as output_stream,
    ):
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT / "backend",
            stdin=input_stream,
            stdout=output_stream,
            stderr=output_stream,
            start_new_session=True,
            close_fds=True,
        )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if _read_pid(state_root) == process.pid and process.poll() is None:
            print("running: YouTube session maintenance enabled")
            return
        if process.poll() is not None:
            break
        time.sleep(0.05)
    if process.poll() is None:
        process.terminate()
    raise SystemExit("YouTube session maintenance failed to start")


def serve_maintainer(
    source_root: Path,
    *,
    state_root: Path = DEFAULT_STATE_ROOT,
    profile: str = DEFAULT_PROFILE,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> int:
    """Refresh in a detached process whose authorization came from its launcher."""
    _require_macos()
    if interval_seconds < 10:
        raise SystemExit("maintenance interval must be at least 10 seconds")
    source_root = source_root.absolute()
    state_root = state_root.absolute()
    _ensure_private_directory(state_root)
    lock = os.open(
        state_root / ".daemon.lock",
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        _validate_private_file(lock, "unsafe maintainer daemon lock")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 4
        stop_requested = False

        def request_stop(_signum: int, _frame: FrameType | None) -> None:
            nonlocal stop_requested
            stop_requested = True

        previous_term = signal.signal(signal.SIGTERM, request_stop)
        previous_int = signal.signal(signal.SIGINT, request_stop)
        _write_pid(state_root, os.getpid())
        try:
            while not stop_requested:
                refresh_youtube_source(
                    source_root, state_root=state_root, profile=profile
                )
                deadline = time.monotonic() + interval_seconds
                while not stop_requested and time.monotonic() < deadline:
                    time.sleep(min(0.25, deadline - time.monotonic()))
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.signal(signal.SIGINT, previous_int)
            _remove_own_pid(state_root)
        return 0
    finally:
        os.close(lock)


def stop_maintainer(state_root: Path = DEFAULT_STATE_ROOT) -> None:
    _require_macos()
    state_root = state_root.absolute()
    pid = _read_pid(state_root)
    if pid is None or not _daemon_running(state_root):
        _remove_stale_pid(state_root)
        print("stopped: YouTube session source retained")
        return
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and _process_exists(pid):
        time.sleep(0.05)
    if _process_exists(pid):
        raise SystemExit("YouTube session maintenance did not stop")
    _remove_stale_pid(state_root)
    print("stopped: YouTube session source retained")


def maintainer_status(state_root: Path = DEFAULT_STATE_ROOT) -> int:
    _require_macos()
    state_root = state_root.absolute()
    state = _read_state(state_root)
    status = str(state.get("status", "pending")) if state else "pending"
    if _daemon_running(state_root):
        print(f"running: {status}")
        return 0
    print(f"stopped: {status}")
    return 4


def _current_payload(source_root: Path) -> bytes | None:
    try:
        return ProviderCookieFile(source_root / "cookies.txt").read(
            ProviderKey.YOUTUBE,
            browser_session_policy(ProviderKey.YOUTUBE).version,
        )
    except Exception:
        return None


def _current_revision(source_root: Path) -> str | None:
    payload = _current_payload(source_root)
    return None if payload is None else hashlib.sha256(payload).hexdigest()


def _write_state(
    state_root: Path,
    *,
    status: MaintenanceResult,
    attempted_at: str,
    revision: str | None,
    succeeded_at: str | None = None,
) -> None:
    previous = _read_state(state_root)
    document = {
        "provider": ProviderKey.YOUTUBE.value,
        "status": status.value,
        "last_attempt_at": attempted_at,
        "last_success_at": succeeded_at
        or (previous.get("last_success_at") if previous else None),
        "revision": revision,
    }
    _atomic_write_json(state_root / "state.json", document)


def _read_state(state_root: Path) -> dict[str, object] | None:
    document = _read_private_json(state_root / "state.json")
    return document if isinstance(document, dict) else None


def _write_pid(state_root: Path, pid: int) -> None:
    _atomic_write_json(state_root / "daemon.json", {"pid": pid})


def _read_pid(state_root: Path) -> int | None:
    try:
        document = _read_private_json(state_root / "daemon.json")
    except OSError:
        return None
    if not isinstance(document, dict):
        return None
    pid = document.get("pid")
    return pid if isinstance(pid, int) and pid > 1 else None


def _daemon_running(state_root: Path) -> bool:
    pid = _read_pid(state_root)
    if pid is None or not _process_exists(pid):
        return False
    result = subprocess.run(
        ("/bin/ps", "-p", str(pid), "-o", "command="),
        check=False,
        capture_output=True,
        text=True,
    )
    command = result.stdout
    return (
        result.returncode == 0
        and "app.runner.provider_session_maintainer serve" in command
        and str(state_root) in command
    )


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _remove_own_pid(state_root: Path) -> None:
    if _read_pid(state_root) == os.getpid():
        (state_root / "daemon.json").unlink(missing_ok=True)


def _remove_stale_pid(state_root: Path) -> None:
    if not _daemon_running(state_root):
        (state_root / "daemon.json").unlink(missing_ok=True)


def _read_private_json(path: Path) -> object | None:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
        )
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "r", encoding="utf-8") as source:
        _validate_private_file(source.fileno(), "unsafe maintainer state")
        try:
            document: object = json.load(source)
            return document
        except (json.JSONDecodeError, UnicodeError):
            return None


def _atomic_write_json(target: Path, document: object) -> None:
    if target.is_symlink():
        raise OSError("unsafe maintainer state")
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}-", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=True) as output:
            json.dump(document, output, ensure_ascii=True, separators=(",", ":"))
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temp.unlink(missing_ok=True)


def _ensure_private_directory(path: Path) -> None:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise OSError("unsafe maintainer directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise OSError("maintainer directory must belong to the current user")
    os.chmod(path, 0o700)


def _validate_private_file(descriptor: int, message: str) -> None:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or info.st_mode & 0o077
    ):
        raise OSError(message)


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit("the YouTube session maintainer requires macOS")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="维护独立 YouTube 会话文件，不在用户请求中读取浏览器"
    )
    parser.add_argument(
        "command", choices=("start", "status", "refresh", "stop", "serve")
    )
    parser.add_argument("--directory", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument(
        "--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _require_macos()
    if args.command == "start":
        start_maintainer(
            args.directory,
            state_root=args.state_root,
            profile=args.profile,
            interval_seconds=args.interval_seconds,
        )
        return 0
    if args.command == "stop":
        stop_maintainer(args.state_root)
        return 0
    if args.command == "status":
        return maintainer_status(args.state_root)
    if args.command == "serve":
        return serve_maintainer(
            args.directory,
            state_root=args.state_root,
            profile=args.profile,
            interval_seconds=args.interval_seconds,
        )
    outcome = refresh_youtube_source(
        args.directory, state_root=args.state_root, profile=args.profile
    )
    print(f"youtube: {outcome.value}")
    return (
        0
        if outcome
        in {
            MaintenanceResult.UPDATED,
            MaintenanceResult.UNCHANGED,
            MaintenanceResult.BUSY,
        }
        else 5
    )


if __name__ == "__main__":
    raise SystemExit(main())
