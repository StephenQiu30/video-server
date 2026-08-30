"""Bounded file-queue client for refreshing operator provider Cookies."""

from __future__ import annotations

import asyncio
import os
import re
import secrets
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from app.runner.errors import RunnerFailure

_TOKEN = re.compile(r"[0-9a-f]{32}")
_RESULTS = {
    b"credential_required": ("credential_required", 422),
    b"provider_session_unavailable": ("provider_session_unavailable", 503),
}
_MAX_TIMEOUT_SECONDS = 20.0


def _new_token() -> str:
    return secrets.token_hex(16)


class ProviderCookieSync(Protocol):
    """Minimal refresh boundary consumed by the provider session store."""

    def is_ready(self) -> bool: ...

    async def sync(self) -> None: ...


class ProviderCookieSyncClient:
    """Request one host-side Cookie refresh without exposing Cookie contents."""

    def __init__(
        self,
        root: Path,
        *,
        timeout_seconds: float = _MAX_TIMEOUT_SECONDS,
        poll_interval_seconds: float = 0.05,
        token_factory: Callable[[], str] = _new_token,
    ) -> None:
        if not root.is_absolute():
            raise ValueError("cookie sync root must be absolute")
        if not 0 < timeout_seconds <= _MAX_TIMEOUT_SECONDS:
            raise ValueError("cookie sync timeout must be between 0 and 20 seconds")
        if poll_interval_seconds <= 0:
            raise ValueError("cookie sync poll interval must be positive")
        self._root = root
        self._timeout = timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._token_factory = token_factory

    def is_ready(self) -> bool:
        try:
            descriptors = self._open_directories()
        except RunnerFailure:
            return False
        self._close_directories(descriptors)
        return True

    async def sync(self) -> None:
        token = self._token_factory()
        if _TOKEN.fullmatch(token) is None:
            raise RunnerFailure("provider_session_unavailable", status=503)
        request_name = f"{token}.request"
        response_name = f"{token}.response"
        root_fd, requests_fd, responses_fd = self._open_directories()
        created = False
        try:
            if _entry_exists(responses_fd, response_name):
                raise RunnerFailure("provider_session_unavailable", status=503)
            descriptor = os.open(
                request_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _no_follow(),
                0o600,
                dir_fd=requests_fd,
            )
            created = True
            try:
                os.fchmod(descriptor, 0o600)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            deadline = asyncio.get_running_loop().time() + self._timeout
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise RunnerFailure("provider_session_unavailable", status=503)
                result = _read_response(responses_fd, response_name)
                if result is not None:
                    if result == b"ok":
                        return
                    code, status = _RESULTS.get(
                        result,
                        ("provider_session_unavailable", 503),
                    )
                    raise RunnerFailure(code, status=status)
                await asyncio.sleep(min(self._poll_interval, remaining))
        except RunnerFailure:
            raise
        except OSError as exc:
            raise RunnerFailure("provider_session_unavailable", status=503) from exc
        finally:
            if created:
                _unlink_quiet(responses_fd, response_name)
                _unlink_quiet(requests_fd, request_name)
            self._close_directories((root_fd, requests_fd, responses_fd))

    def _open_directories(self) -> tuple[int, int, int]:
        descriptors: list[int] = []
        try:
            root_fd = _open_directory(self._root)
            descriptors.append(root_fd)
            requests_fd = _open_directory("requests", dir_fd=root_fd)
            descriptors.append(requests_fd)
            responses_fd = _open_directory("responses", dir_fd=root_fd)
            descriptors.append(responses_fd)
            return root_fd, requests_fd, responses_fd
        except OSError as exc:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
            raise RunnerFailure("provider_session_unavailable", status=503) from exc

    @staticmethod
    def _close_directories(descriptors: tuple[int, int, int]) -> None:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _open_directory(path: str | Path, *, dir_fd: int | None = None) -> int:
    before = os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
    if not stat.S_ISDIR(before.st_mode):
        raise OSError("cookie sync path is not a directory")
    descriptor = os.open(
        path,
        getattr(os, "O_PATH", os.O_RDONLY)
        | getattr(os, "O_DIRECTORY", 0)
        | _no_follow(),
        dir_fd=dir_fd,
    )
    current = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(current.st_mode)
        or current.st_dev != before.st_dev
        or current.st_ino != before.st_ino
    ):
        os.close(descriptor)
        raise OSError("cookie sync path is not a directory")
    return descriptor


def _entry_exists(directory_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _read_response(directory_fd: int, name: str) -> bytes | None:
    try:
        before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode) or before.st_size > 32:
        raise RunnerFailure("provider_session_unavailable", status=503)
    descriptor = os.open(name, os.O_RDONLY | _no_follow(), dir_fd=directory_fd)
    with os.fdopen(descriptor, "rb", closefd=True) as response:
        current = os.fstat(response.fileno())
        if current.st_ino != before.st_ino or not stat.S_ISREG(current.st_mode):
            raise RunnerFailure("provider_session_unavailable", status=503)
        return response.read(33)


def _unlink_quiet(directory_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=directory_fd)
    except OSError:
        pass


def _no_follow() -> int:
    return getattr(os, "O_NOFOLLOW", 0)
