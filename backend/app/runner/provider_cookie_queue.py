"""One-shot host queue for on-demand provider session refreshes."""

from __future__ import annotations

import os
import re
import secrets
import stat
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
    decode_public_key,
    encode_public_key,
)
from app.runner.provider_session_policy import browser_session_policy

_REQUEST = re.compile(r"(?P<token>[0-9a-f]{32})\.request")
DEFAULT_ACK_TIMEOUT_SECONDS = 1.0
AGENT_READY_MARKER = ".agent-installed"
AGENT_READY_PAYLOAD = b"provider-cookie-agent\n"
_MAX_REQUEST_BYTES = 128


@dataclass(frozen=True, slots=True)
class ProviderCookieRequest:
    provider: ProviderKey
    version: ProviderSessionVersion
    public_key: bytes

    def serialize(self) -> bytes:
        encoded_key = encode_public_key(self.public_key)
        return f"{self.provider.value}\n{self.version.value}\n{encoded_key}\n".encode(
            "ascii"
        )

    @classmethod
    def parse(cls, payload: bytes) -> ProviderCookieRequest:
        try:
            provider_value, version_value, key_value, trailer = payload.decode(
                "ascii"
            ).split("\n")
            provider = ProviderKey(provider_value)
            version = ProviderSessionVersion(version_value)
            public_key = decode_public_key(key_value)
            if trailer or browser_session_policy(provider).version is not version:
                raise ValueError("invalid provider Cookie request")
        except (RunnerFailure, UnicodeDecodeError, ValueError) as exc:
            raise ValueError("invalid provider Cookie request") from exc
        return cls(provider, version, public_key)


def prepare_runtime(runtime_root: Path) -> tuple[Path, Path]:
    """Create the queue directories shared with the isolated runner."""
    requests = runtime_root / "requests"
    responses = runtime_root / "responses"
    _secure_directory(runtime_root, 0o711)
    for directory in (requests, responses):
        _secure_directory(directory, 0o733)
    quarantine = runtime_root / ".discarded"
    _secure_directory(quarantine, 0o700)
    return requests, responses


def drain_request_batch(
    runtime_root: Path,
    expected_provider: ProviderKey,
    refresh: Callable[[ProviderKey, ProviderSessionVersion], ProviderCookieLease],
    publish: Callable[[Path, ProviderCookieRequest, ProviderCookieLease], None],
    *,
    acknowledgement_timeout_seconds: float = DEFAULT_ACK_TIMEOUT_SECONDS,
) -> None:
    """Serve one snapshot so launchd can schedule later arrivals separately."""
    requests, responses = prepare_runtime(runtime_root)
    pending = _pending_requests(requests, expected_provider)
    if not pending:
        return
    published: list[tuple[Path, Path]] = []
    try:
        results: dict[
            tuple[ProviderKey, ProviderSessionVersion], ProviderCookieLease
        ] = {}
        for request, token, requested in pending:
            response = responses / f"{token}.response"
            did_publish = False
            try:
                if _is_regular_request(request):
                    key = requested.provider, requested.version
                    if key not in results:
                        try:
                            results[key] = refresh(
                                requested.provider, requested.version
                            )
                        except Exception:
                            results[key] = ProviderCookieLease(
                                ProviderCookieLeaseStatus.SESSION_UNAVAILABLE
                            )
                    result = results[key]
                    publish(response, requested, result)
                    published.append((request, response))
                    did_publish = True
            except Exception:
                _remove_entry(response)
            finally:
                if not did_publish:
                    _remove_entry(response)
                    _remove_entry(request)
        _wait_for_ack(published, acknowledgement_timeout_seconds)
        _cleanup_published(published)
    except BaseException:
        _cleanup_published(published)
        for request, token, _requested in pending:
            _remove_entry(responses / f"{token}.response")
            _remove_entry(request)
        raise


def _pending_requests(
    directory: Path,
    expected_provider: ProviderKey,
) -> tuple[tuple[Path, str, ProviderCookieRequest], ...]:
    pending: list[tuple[Path, str, ProviderCookieRequest]] = []
    for request in directory.iterdir():
        match = _REQUEST.fullmatch(request.name)
        try:
            info = request.lstat()
        except FileNotFoundError:
            continue
        try:
            if (
                match is None
                or not stat.S_ISREG(info.st_mode)
                or not 0 < info.st_size <= _MAX_REQUEST_BYTES
            ):
                raise ValueError("invalid provider Cookie request")
            descriptor = os.open(request, os.O_RDONLY | _no_follow())
            with os.fdopen(descriptor, "rb", closefd=True) as source:
                opened = os.fstat(source.fileno())
                if opened.st_ino != info.st_ino or not stat.S_ISREG(opened.st_mode):
                    raise ValueError("provider Cookie request changed")
                payload = source.read(_MAX_REQUEST_BYTES + 1)
            if len(payload) > _MAX_REQUEST_BYTES:
                raise ValueError("provider Cookie request changed")
            requested = ProviderCookieRequest.parse(payload)
            if requested.provider is not expected_provider:
                raise ValueError("provider Cookie request crossed its queue boundary")
        except (OSError, ValueError):
            _remove_entry(request)
            continue
        pending.append((request, match.group("token"), requested))
    return tuple(sorted(pending, key=lambda item: item[1]))


def _wait_for_ack(published: list[tuple[Path, Path]], timeout: float) -> None:
    deadline = time.monotonic() + max(0.0, timeout)
    while any(_is_regular_request(request) for request, _ in published):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.01, remaining))


def _cleanup_published(published: list[tuple[Path, Path]]) -> None:
    for request, response in published:
        _remove_entry(response)
        _remove_entry(request)


def _is_regular_request(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(info.st_mode) and 0 < info.st_size <= _MAX_REQUEST_BYTES


def _remove_entry(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if not stat.S_ISDIR(info.st_mode):
        try:
            path.unlink()
            return
        except FileNotFoundError:
            return
        except OSError:
            pass
    if stat.S_ISDIR(info.st_mode):
        os.chmod(path, 0o700, follow_symlinks=False)
    quarantine = path.parent.parent / ".discarded"
    discarded = quarantine / secrets.token_hex(16)
    try:
        os.replace(path, discarded)
    except FileNotFoundError:
        return


def _secure_directory(directory: Path, mode: int) -> None:
    directory.mkdir(mode=mode, parents=True, exist_ok=True)
    info = directory.lstat()
    if directory.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe Cookie synchronization directory")
    os.chmod(directory, mode)


def _no_follow() -> int:
    return getattr(os, "O_NOFOLLOW", 0)
