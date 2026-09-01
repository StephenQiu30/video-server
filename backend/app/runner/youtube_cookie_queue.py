"""One-shot host queue for on-demand provider session refreshes."""

from __future__ import annotations

import os
import re
import secrets
import stat
import time
from collections.abc import Callable
from pathlib import Path

_REQUEST = re.compile(r"(?P<token>[0-9a-f]{32})\.request")
DEFAULT_ACK_TIMEOUT_SECONDS = 1.0
AGENT_READY_MARKER = ".agent-installed"


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
    refresh: Callable[[], str],
    publish: Callable[[Path, str], None],
    *,
    acknowledgement_timeout_seconds: float = DEFAULT_ACK_TIMEOUT_SECONDS,
) -> None:
    """Serve one snapshot so launchd can schedule later arrivals separately."""
    requests, responses = prepare_runtime(runtime_root)
    pending = _pending_requests(requests)
    if not pending:
        return
    published: list[tuple[Path, Path]] = []
    try:
        try:
            result = refresh()
        except Exception:
            result = "provider_session_unavailable"
        for request, token in pending:
            response = responses / f"{token}.response"
            did_publish = False
            try:
                if _is_empty_regular(request):
                    publish(response, result)
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
        for request, token in pending:
            _remove_entry(responses / f"{token}.response")
            _remove_entry(request)
        raise


def _pending_requests(directory: Path) -> tuple[tuple[Path, str], ...]:
    pending: list[tuple[Path, str]] = []
    for request in directory.iterdir():
        match = _REQUEST.fullmatch(request.name)
        try:
            info = request.lstat()
        except FileNotFoundError:
            continue
        if match and stat.S_ISREG(info.st_mode) and info.st_size == 0:
            pending.append((request, match.group("token")))
        else:
            _remove_entry(request)
    return tuple(sorted(pending, key=lambda item: item[1]))


def _wait_for_ack(published: list[tuple[Path, Path]], timeout: float) -> None:
    deadline = time.monotonic() + max(0.0, timeout)
    while any(_is_empty_regular(request) for request, _ in published):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.01, remaining))


def _cleanup_published(published: list[tuple[Path, Path]]) -> None:
    for request, response in published:
        _remove_entry(response)
        _remove_entry(request)


def _is_empty_regular(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(info.st_mode) and info.st_size == 0


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
