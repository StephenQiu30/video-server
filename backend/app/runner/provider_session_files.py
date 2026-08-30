"""Private Cookie file validation and per-operation materialization."""

from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.runner.errors import RunnerFailure

_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_NETSCAPE_HEADERS = (
    b"# Netscape HTTP Cookie File",
    b"# HTTP Cookie File",
)
_MAX_COOKIE_BYTES = 1024**2


def prepare_private_root(root: Path) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise RunnerFailure("provider_session_unavailable", status=503)
    os.chmod(root, 0o700)


def validated_cookie_payload(
    source_root: Path,
    provider: str,
    version: str,
    allowlist: frozenset[str],
    *,
    now: float,
    max_age_seconds: float,
) -> bytes:
    if _VERSION.fullmatch(version) is None:
        raise RunnerFailure("credential_rejected", status=422)
    candidate = source_root / provider / f"{version}.cookies.txt"
    if candidate.is_symlink():
        raise RunnerFailure("credential_rejected", status=422)
    source = candidate.resolve()
    if not source.is_relative_to(source_root):
        raise RunnerFailure("credential_rejected", status=422)
    _validate_freshness(source, now, max_age_seconds)
    payload = _read_regular_file(source)
    _validate_netscape_cookie(payload, allowlist)
    return payload


@contextmanager
def operation_cookie(payload: bytes, temp_root: Path, provider: str) -> Iterator[Path]:
    operation_dir = Path(tempfile.mkdtemp(prefix=f"{provider}-", dir=temp_root))
    os.chmod(operation_dir, 0o700)
    jar = operation_dir / "cookies.txt"
    try:
        descriptor = os.open(
            jar,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _no_follow(),
            0o600,
        )
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        if os.name == "posix" and stat.S_IMODE(jar.stat().st_mode) != 0o600:
            raise RunnerFailure("provider_session_unavailable", status=503)
        yield jar
    finally:
        shutil.rmtree(operation_dir, ignore_errors=True)


def _validate_freshness(source: Path, now: float, max_age_seconds: float) -> None:
    if max_age_seconds <= 0:
        return
    try:
        age = now - source.stat().st_mtime
    except OSError as exc:
        raise RunnerFailure("credential_required", status=422) from exc
    if age < 0 or age > max_age_seconds:
        raise RunnerFailure("provider_session_unavailable", status=503)


def _read_regular_file(path: Path) -> bytes:
    try:
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise RunnerFailure("credential_rejected", status=422)
        if info.st_size <= 0 or info.st_size > _MAX_COOKIE_BYTES:
            raise RunnerFailure("credential_rejected", status=422)
        descriptor = os.open(path, os.O_RDONLY | _no_follow())
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode) or current.st_ino != info.st_ino:
            os.close(descriptor)
            raise RunnerFailure("credential_rejected", status=422)
        with os.fdopen(descriptor, "rb", closefd=True) as source:
            payload = source.read(_MAX_COOKIE_BYTES + 1)
    except RunnerFailure:
        raise
    except OSError as exc:
        raise RunnerFailure("credential_required", status=422) from exc
    if len(payload) > _MAX_COOKIE_BYTES:
        raise RunnerFailure("credential_rejected", status=422)
    return payload


def _validate_netscape_cookie(payload: bytes, allowlist: frozenset[str]) -> None:
    lines = payload.splitlines()
    if not lines or not any(lines[0].startswith(item) for item in _NETSCAPE_HEADERS):
        raise RunnerFailure("credential_rejected", status=422)
    found = False
    for line in lines[1:]:
        if not line or (line.startswith(b"#") and not line.startswith(b"#HttpOnly_")):
            continue
        fields = line.split(b"\t")
        if len(fields) != 7:
            raise RunnerFailure("credential_rejected", status=422)
        try:
            domain = fields[0].removeprefix(b"#HttpOnly_").decode("ascii")
        except UnicodeDecodeError as exc:
            raise RunnerFailure("credential_rejected", status=422) from exc
        normalized = domain.lstrip(".").casefold()
        if not any(
            normalized == item or normalized.endswith(f".{item}") for item in allowlist
        ):
            raise RunnerFailure("credential_rejected", status=422)
        found = True
    if not found:
        raise RunnerFailure("credential_rejected", status=422)


def _no_follow() -> int:
    return getattr(os, "O_NOFOLLOW", 0)
