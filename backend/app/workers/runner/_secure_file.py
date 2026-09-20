"""Small shared primitives for private runner files and atomic writes."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import cast


def no_follow_flag() -> int:
    """Return the platform flag that prevents opening a symlink."""
    return getattr(os, "O_NOFOLLOW", 0)


def ensure_private_directory(path: Path) -> None:
    """Create and validate a directory owned and readable only by this user."""
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise OSError("unsafe private directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow_flag(),
    )
    try:
        os.fchmod(descriptor, 0o700)
        validate_private_directory(descriptor, "unsafe private directory")
    finally:
        os.close(descriptor)


def validate_private_directory(descriptor: int, message: str) -> None:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink < 2
        or info.st_mode & 0o077
    ):
        raise OSError(message)


def validate_private_file(descriptor: int, message: str) -> None:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or info.st_mode & 0o077
    ):
        raise OSError(message)


def read_private_json(
    path: Path, *, message: str, max_bytes: int = 64 * 1024
) -> object | None:
    """Read one private JSON file without following a symlink."""
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_NONBLOCK | no_follow_flag(),
        )
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb", closefd=True) as source:
        validate_private_file(source.fileno(), message)
        payload = source.read(max_bytes + 1)
    if len(payload) > max_bytes:
        return None
    try:
        return cast(object, json.loads(payload.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeError):
        return None


def atomic_write_bytes(target: Path, payload: bytes, *, mode: int = 0o600) -> None:
    """Write bytes through a private temporary file and fsync the directory."""
    if target.is_symlink():
        raise OSError("unsafe atomic-write target")
    descriptor, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}-", dir=target.parent
    )
    temp = Path(raw_temp)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            descriptor = -1
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, target)
        directory = os.open(
            target.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow_flag(),
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temp.unlink(missing_ok=True)


def atomic_write_json(target: Path, document: object) -> None:
    atomic_write_bytes(
        target,
        (json.dumps(document, ensure_ascii=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        ),
    )
