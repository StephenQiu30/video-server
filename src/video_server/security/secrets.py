"""Strict local secret-file loading boundary."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from video_server.security._darwin_acl import ensure_no_extended_acl

_MAX_SECRET_BYTES = 64 * 1024


def _validate_metadata(metadata: os.stat_result) -> None:
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("secret path must be a regular file")
    if metadata.st_uid != os.geteuid():
        raise ValueError("secret file must be owned by the current user")
    if metadata.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError("secret file must not grant group or other permissions")


def _open_validated(path: Path) -> tuple[int, os.stat_result]:
    try:
        initial = os.lstat(path)
    except OSError as error:
        raise ValueError("secret path cannot be inspected") from error
    _validate_metadata(initial)

    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError("secret file cannot be opened safely") from error

    try:
        opened = os.fstat(descriptor)
        _validate_metadata(opened)
        if (opened.st_dev, opened.st_ino) != (initial.st_dev, initial.st_ino):
            raise ValueError("secret path changed while being opened")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor, opened


def _validate_size(metadata: os.stat_result, *, expected_size: int | None) -> int:
    if metadata.st_size <= 0:
        raise ValueError("secret file must not be empty")
    if metadata.st_size > _MAX_SECRET_BYTES:
        raise ValueError("secret file exceeds the maximum size")
    if expected_size is not None and metadata.st_size != expected_size:
        raise ValueError("secret file has an unexpected size")
    return expected_size if expected_size is not None else _MAX_SECRET_BYTES


def _read_bounded(descriptor: int, *, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit + 1
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_exact_file(path: Path, *, expected_size: int | None) -> bytes:
    descriptor, opened = _open_validated(path)
    try:
        ensure_no_extended_acl(descriptor)
        limit = _validate_size(opened, expected_size=expected_size)
        secret = _read_bounded(descriptor, limit=limit)
        ensure_no_extended_acl(descriptor)
        final = os.fstat(descriptor)
        _validate_metadata(final)
        _validate_size(final, expected_size=expected_size)
    except OSError as error:
        raise ValueError("secret file could not be read") from error
    finally:
        os.close(descriptor)

    if len(secret) > limit:
        raise ValueError("secret file exceeds the allowed read size")
    if expected_size is not None and len(secret) != expected_size:
        raise ValueError("secret file has an unexpected size")
    return secret


def load_secret_bytes(path: str | Path, *, expected_size: int | None = None) -> bytes:
    """Load an owner-only regular file without normalizing its bytes."""

    if expected_size is not None and not 0 < expected_size <= _MAX_SECRET_BYTES:
        raise ValueError("expected secret size exceeds the allowed range")

    return _read_exact_file(Path(path), expected_size=expected_size)


def load_secret_text(path: str | Path) -> str:
    """Load a non-empty UTF-8 secret without trimming or normalization."""

    return load_secret_bytes(path).decode("utf-8", errors="strict")
