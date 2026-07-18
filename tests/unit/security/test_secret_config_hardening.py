from __future__ import annotations

import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from video_server.config import validate_bind_host
from video_server.errors import DomainError
from video_server.security import secrets as secret_module
from video_server.security.secrets import load_secret_bytes, load_secret_text

MAX_SECRET_BYTES = 64 * 1024


class _FailingProvider:
    def __init__(self, result: bool | None = False, error: Exception | None = None) -> None:
        self._result = result
        self._error = error

    def validate_startup(self) -> bool | None:
        if self._error is not None:
            raise self._error
        return self._result


def _write_secret(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def _assert_bind_rejected(provider: object | None) -> None:
    with pytest.raises((DomainError, ValueError)):
        validate_bind_host("0.0.0.0", principal_provider=provider)


@pytest.mark.security
@pytest.mark.skipif(sys.platform != "darwin", reason="Darwin ACL semantics")
def test_secret_rejects_darwin_acl_that_grants_everyone_read(tmp_path: Path) -> None:
    path = _write_secret(tmp_path / "acl-secret", b"secret")
    subprocess.run(
        ["chmod", "+a", "everyone allow read", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert stat.S_IMODE(path.stat().st_mode) == 0o600

    with pytest.raises(ValueError):
        load_secret_bytes(path)


@pytest.mark.security
def test_exact_size_mismatch_stops_after_expected_size_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_secret(tmp_path / "oversized-key", b"x" * (2 * 1024 * 1024))
    original_read = os.read
    read_calls = 0
    bytes_read = 0

    def tracked_read(descriptor: int, size: int) -> bytes:
        nonlocal bytes_read, read_calls
        chunk = original_read(descriptor, size)
        read_calls += 1
        bytes_read += len(chunk)
        return chunk

    monkeypatch.setattr(secret_module.os, "read", tracked_read)

    with pytest.raises(ValueError):
        load_secret_bytes(path, expected_size=32)

    assert bytes_read <= 33
    assert read_calls <= 2


@pytest.mark.security
@pytest.mark.parametrize("loader", [load_secret_bytes, load_secret_text])
def test_generic_secret_rejects_more_than_64_kib(
    tmp_path: Path,
    loader: Callable[[str | Path], bytes | str],
) -> None:
    at_limit = _write_secret(tmp_path / "at-limit", b"x" * MAX_SECRET_BYTES)
    oversized = _write_secret(tmp_path / "oversized", b"x" * (MAX_SECRET_BYTES + 1))

    assert len(loader(at_limit)) == MAX_SECRET_BYTES
    with pytest.raises(ValueError):
        loader(oversized)


@pytest.mark.security
def test_exact_size_cannot_override_generic_64_kib_limit(tmp_path: Path) -> None:
    oversized = _write_secret(tmp_path / "oversized", b"x" * (MAX_SECRET_BYTES + 1))

    with pytest.raises(ValueError):
        load_secret_bytes(oversized, expected_size=MAX_SECRET_BYTES + 1)


@pytest.mark.security
@pytest.mark.parametrize(
    "provider",
    [
        None,
        object(),
        True,
        _FailingProvider(False),
        _FailingProvider(None),
        _FailingProvider(error=RuntimeError("provider unavailable")),
    ],
)
def test_non_loopback_bind_rejects_unverified_principal_provider(provider: object | None) -> None:
    _assert_bind_rejected(provider)
