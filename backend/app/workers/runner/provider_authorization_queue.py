"""Filesystem queue for one-time, browser-based provider authorization."""

from __future__ import annotations

import os
import re
import secrets
import stat
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.services.provider_authorization import ProviderAuthorizationRequest
from app.services.provider_types import (
    ProviderAuthorizationSource,
    ProviderKey,
)
from app.workers.runner._secure_file import atomic_write_bytes, no_follow_flag
from app.workers.runner.provider_cookie_queue import prepare_runtime

_TOKEN = re.compile(r"[0-9a-f]{32}")
_MAX_REQUEST_BYTES = 256
AUTHORIZATION_RUNTIME = "control"
AUTHORIZATION_READY_MARKER = ".agent-installed"
AUTHORIZATION_READY_PAYLOAD = b"provider-cookie-agent\n"
AUTHORIZATION_SOURCE_DIRECTORY = "authorization-sources"
_MAX_SOURCE_BYTES = 64
DEFAULT_AGENT_PROBE_TIMEOUT_SECONDS = 3.0


def authorization_runtime(root: Path) -> Path:
    """Return the shared control queue below the installed agent runtime."""

    return root / AUTHORIZATION_RUNTIME


def prepare_authorization_runtime(root: Path) -> tuple[Path, Path, Path]:
    """Initialize host-owned control directories before exposing the queue."""

    runtime = authorization_runtime(root)
    requests, responses = prepare_runtime(runtime)
    cancelled = runtime / "cancelled"
    _secure_directory(cancelled, 0o733)
    # Source choice is host-only state. Keep it outside the API-mounted
    # ``control`` subtree because Docker Desktop does not reliably preserve
    # host POSIX directory permissions across bind mounts.
    _secure_directory(root / AUTHORIZATION_SOURCE_DIRECTORY, 0o700)
    return requests, responses, cancelled


def _authorization_paths(root: Path) -> tuple[Path, Path, Path]:
    """Validate shared paths without changing host-owned permissions."""

    runtime = authorization_runtime(root)
    paths = (
        runtime / "requests",
        runtime / "responses",
        runtime / "cancelled",
    )
    for directory in (runtime, *paths):
        try:
            info = directory.lstat()
        except FileNotFoundError as exc:
            raise OSError("authorization queue is not initialized") from exc
        if directory.is_symlink() or not stat.S_ISDIR(info.st_mode):
            raise OSError("unsafe authorization queue directory")
    return paths


class FileProviderAuthorizationQueue:
    """Adapt the host filesystem queue to the service-layer port."""

    def __init__(
        self,
        root: Path,
        *,
        probe_timeout_seconds: float = DEFAULT_AGENT_PROBE_TIMEOUT_SECONDS,
    ) -> None:
        if not root.is_absolute():
            raise ValueError("provider authorization queue root must be absolute")
        self._root = root
        self._probe_timeout_seconds = probe_timeout_seconds

    def agent_ready(self, provider: ProviderKey) -> bool:
        if not authorization_agent_ready(self._root):
            return False
        if self._probe_timeout_seconds <= 0:
            return True
        token = secrets.token_hex(16)
        try:
            write_authorization_request(
                self._root,
                token,
                ProviderAuthorizationRequest(
                    provider,
                    datetime.now(UTC) + timedelta(seconds=5),
                    ProviderAuthorizationSource.DEDICATED_CHROME,
                    probe=True,
                ),
            )
        except OSError:
            return False
        deadline = time.monotonic() + self._probe_timeout_seconds
        while time.monotonic() < deadline:
            if read_authorization_response(self._root, token) == "agent_ready":
                remove_authorization_response(self._root, token)
                return True
            time.sleep(0.05)
        cancel_authorization(self._root, token)
        return False

    def write_request(self, token: str, request: ProviderAuthorizationRequest) -> None:
        write_authorization_request(self._root, token, request)

    def read_response(self, token: str) -> str | None:
        return read_authorization_response(self._root, token)

    def remove_response(self, token: str) -> None:
        remove_authorization_response(self._root, token)

    def cancel(self, token: str) -> None:
        cancel_authorization(self._root, token)

    def cleanup(self, token: str) -> None:
        if _TOKEN.fullmatch(token) is None:
            raise ValueError("invalid authorization transaction token")
        requests, responses, cancelled = _authorization_paths(self._root)
        # Called only after the durable operation and its retention deadline end.
        for directory, suffix in (
            (requests, "request"),
            (responses, "response"),
            (cancelled, "cancel"),
        ):
            (directory / f"{token}.{suffix}").unlink(missing_ok=True)


def write_authorization_source(
    root: Path,
    provider: ProviderKey,
    source: ProviderAuthorizationSource,
) -> None:
    """Persist only the non-secret source choice for future refreshes."""

    prepare_authorization_runtime(root)
    target = root / AUTHORIZATION_SOURCE_DIRECTORY / f"{provider.value}.source"
    atomic_write_bytes(target, f"{source.value}\n".encode("ascii"), mode=0o600)


def read_authorization_source(
    root: Path, provider: ProviderKey
) -> ProviderAuthorizationSource | None:
    """Read a bounded source marker without following a symlink."""

    prepare_authorization_runtime(root)
    path = root / AUTHORIZATION_SOURCE_DIRECTORY / f"{provider.value}.source"
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | no_follow_flag())
        with os.fdopen(descriptor, "rb", closefd=True) as source:
            info = os.fstat(source.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size > _MAX_SOURCE_BYTES
            ):
                return None
            payload = source.read(_MAX_SOURCE_BYTES + 1)
            if len(payload) > _MAX_SOURCE_BYTES:
                return None
            value = payload.decode("ascii").strip()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    if not value:
        return None
    try:
        return ProviderAuthorizationSource(value)
    except ValueError:
        return None


def authorization_agent_ready(root: Path) -> bool:
    """Check the host agent marker without following a bind-mounted symlink."""

    runtime = authorization_runtime(root)
    try:
        runtime_descriptor = os.open(
            runtime,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow_flag(),
        )
    except OSError:
        return False
    try:
        info = os.stat(
            AUTHORIZATION_READY_MARKER,
            dir_fd=runtime_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return False
        marker_descriptor = os.open(
            AUTHORIZATION_READY_MARKER,
            os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
            dir_fd=runtime_descriptor,
        )
        with os.fdopen(marker_descriptor, "rb", closefd=True) as marker:
            return marker.read(len(AUTHORIZATION_READY_PAYLOAD) + 1) == (
                AUTHORIZATION_READY_PAYLOAD
            )
    except OSError:
        return False
    finally:
        os.close(runtime_descriptor)


def write_authorization_request(
    root: Path,
    token: str,
    request: ProviderAuthorizationRequest,
) -> None:
    """Atomically enqueue one authorization request."""

    if _TOKEN.fullmatch(token) is None:
        raise ValueError("invalid authorization transaction token")
    requests, _, cancelled = _authorization_paths(root)
    if (cancelled / f"{token}.cancel").exists():
        return
    target = requests / f"{token}.request"
    try:
        _atomic_publish_shared(target, request.serialize())
    except FileExistsError:
        if read_authorization_request(target) != request:
            raise OSError("authorization request identity mismatch") from None


def read_authorization_request(path: Path) -> ProviderAuthorizationRequest:
    """Read one request without following a symlink or accepting a large file."""

    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | no_follow_flag())
    with os.fdopen(descriptor, "rb", closefd=True) as request:
        info = os.fstat(request.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or not 0 < info.st_size <= _MAX_REQUEST_BYTES
        ):
            raise ValueError("invalid authorization request")
        payload = request.read(_MAX_REQUEST_BYTES + 1)
    if len(payload) > _MAX_REQUEST_BYTES:
        raise ValueError("authorization request changed")
    return ProviderAuthorizationRequest.parse(payload)


def pending_authorization_request(
    root: Path, token: str
) -> ProviderAuthorizationRequest | None:
    """Resolve a browser bridge token only while its API intent is pending."""

    if _TOKEN.fullmatch(token) is None:
        return None
    try:
        requests, _, _ = _authorization_paths(root)
        return read_authorization_request(requests / f"{token}.request")
    except (FileNotFoundError, OSError, ValueError):
        return None


def read_authorization_response(root: Path, token: str) -> str | None:
    """Read a bounded agent status without exposing any session material."""

    if _TOKEN.fullmatch(token) is None:
        return None
    _, responses, _ = _authorization_paths(root)
    path = responses / f"{token}.response"
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | no_follow_flag())
        with os.fdopen(descriptor, "rb", closefd=True) as response:
            info = os.fstat(response.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size > 64
            ):
                return None
            value = response.read(65).decode("ascii").strip()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return None
    if not value or any(
        character not in "abcdefghijklmnopqrstuvwxyz_-" for character in value
    ):
        return None
    return value


def remove_authorization_response(root: Path, token: str) -> None:
    """Remove a consumed authorization status without following a symlink."""

    if _TOKEN.fullmatch(token) is None:
        return
    _, responses, _ = _authorization_paths(root)
    path = responses / f"{token}.response"
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        raise OSError("authorization response is a directory")
    path.unlink()


def cancel_authorization(root: Path, token: str) -> None:
    """Publish a cancellation marker for an in-flight browser operation."""

    if _TOKEN.fullmatch(token) is None:
        return
    _, _, cancelled = _authorization_paths(root)
    marker = cancelled / f"{token}.cancel"
    try:
        descriptor = os.open(
            marker,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow_flag(),
            0o644,
        )
    except FileExistsError:
        return
    os.close(descriptor)


def _atomic_publish_shared(target: Path, payload: bytes) -> None:
    """Publish a non-secret queue message only after its bytes are durable."""

    if target.is_symlink():
        raise OSError("unsafe authorization queue target")
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.stem}-", suffix=".tmp", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            descriptor = -1
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.link(temp, target)
        temp.unlink()
        try:
            directory = os.open(
                target.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow_flag(),
            )
        except PermissionError:
            # A write-only shared queue deliberately does not grant directory
            # listing to the API container. The host owner fsyncs while consuming.
            return
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temp.unlink(missing_ok=True)


def _secure_directory(directory: Path, mode: int) -> None:
    directory.mkdir(mode=mode, parents=True, exist_ok=True)
    info = directory.lstat()
    if directory.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe authorization queue directory")
    os.chmod(directory, mode)
