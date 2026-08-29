"""Host-wide process lock for the per-user analysis Agent."""

from __future__ import annotations

import errno
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO

from app.workers.analysis.agent_platforms import agent_paths


class AnalysisAgentAlreadyRunning(RuntimeError):
    """Raised when another process owns the current user's Agent lock."""


@contextmanager
def analysis_agent_process_lock() -> Iterator[None]:
    target = agent_paths().stdout.with_name("analysis-agent.lock")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_CREAT | os.O_RDWR, 0o600)
    stream = os.fdopen(descriptor, "r+b")
    try:
        _ensure_lock_byte(stream)
        try:
            _lock(stream)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise AnalysisAgentAlreadyRunning(
                    "analysis agent is already running for this user"
                ) from None
            raise
        try:
            yield
        finally:
            _unlock(stream)
    finally:
        stream.close()


def _ensure_lock_byte(stream: BinaryIO) -> None:
    stream.seek(0, os.SEEK_END)
    if stream.tell() == 0:
        stream.write(b"\0")
        stream.flush()
    stream.seek(0)


def _lock(stream: BinaryIO) -> None:
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(stream: BinaryIO) -> None:
    stream.seek(0)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
