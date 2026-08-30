"""Crash-bounded publication of the minimal provider Cookie file."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def prepare_secret_root(secret_root: Path) -> None:
    secret_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = secret_root.lstat()
    if secret_root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise OSError("unsafe Cookie synchronization directory")
    os.chmod(secret_root, 0o700)


def create_cookie_staging(secret_root: Path, version: str) -> Path:
    """Create the single crash-recoverable staging file for one operator."""
    if _VERSION.fullmatch(version) is None:
        raise OSError("unsafe Cookie version")
    prepare_secret_root(secret_root)
    staging = _staging_path(secret_root, version)
    try:
        descriptor = _open_new(staging)
    except FileExistsError:
        _remove_stale_staging(staging)
        descriptor = _open_new(staging)
    os.close(descriptor)
    return staging


def publish_cookie_payload(
    secret_root: Path,
    version: str,
    payload: bytes,
    staging: Path | None = None,
) -> None:
    target = secret_root / f"{version}.cookies.txt"
    active = staging or create_cookie_staging(secret_root, version)
    if active != _staging_path(secret_root, version):
        raise OSError("unsafe Cookie staging path")
    descriptor = os.open(
        active,
        os.O_WRONLY | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError("unsafe Cookie staging file")
        with os.fdopen(descriptor, "wb", closefd=False) as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        visible = active.lstat()
        if (visible.st_dev, visible.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError("Cookie staging file changed")
        os.replace(active, target)
        _fsync_directory(secret_root)
    finally:
        os.close(descriptor)
        active.unlink(missing_ok=True)


def _staging_path(secret_root: Path, version: str) -> Path:
    return secret_root / f".{version}.cookies.staging"


def _open_new(path: Path) -> int:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        os.fchmod(descriptor, 0o600)
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    return descriptor


def _remove_stale_staging(path: Path) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise OSError("unsafe Cookie staging file")
    path.unlink()


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
