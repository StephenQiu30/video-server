"""Private Cookie file validation and per-operation materialization."""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.runner.errors import RunnerFailure

_NETSCAPE_HEADERS = (
    b"# Netscape HTTP Cookie File",
    b"# HTTP Cookie File",
)
_MAX_COOKIE_BYTES = 1024**2
_MEMORY_FILESYSTEMS = frozenset({"tmpfs", "ramfs"})


def prepare_private_root(root: Path) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise RunnerFailure("provider_session_unavailable", status=503)
    os.chmod(root, 0o700)


def require_memory_backed_root(
    root: Path,
    *,
    mountinfo: Path = Path("/proc/self/mountinfo"),
) -> None:
    """Fail closed unless the operation root lives on a Linux memory filesystem."""
    if sys.platform != "linux":
        raise RunnerFailure("provider_session_unavailable", status=503)
    try:
        resolved = root.resolve(strict=True)
        candidates: list[tuple[int, str]] = []
        for line in mountinfo.read_text(encoding="utf-8").splitlines():
            before, after = line.split(" - ", 1)
            fields = before.split()
            filesystem = after.split()[0]
            mount_point = Path(_decode_mount_path(fields[4])).resolve()
            if resolved == mount_point or resolved.is_relative_to(mount_point):
                candidates.append((len(mount_point.parts), filesystem))
        if not candidates or max(candidates)[1] not in _MEMORY_FILESYSTEMS:
            raise RunnerFailure("provider_session_unavailable", status=503)
    except RunnerFailure:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise RunnerFailure("provider_session_unavailable", status=503) from exc


def validated_cookie_payload(
    payload: bytes,
    allowlist: frozenset[str],
) -> bytes:
    """Validate one in-memory lease without reading a retained source file."""
    if not 0 < len(payload) <= _MAX_COOKIE_BYTES:
        raise RunnerFailure("credential_rejected", status=422)
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
        shutil.rmtree(operation_dir)


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


def _decode_mount_path(value: str) -> str:
    return (
        value.replace(r"\040", " ")
        .replace(r"\011", "\t")
        .replace(r"\012", "\n")
        .replace(r"\134", "\\")
    )
