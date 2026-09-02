"""Cancellation-safe lifecycle helpers for provider Cookie extraction."""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from types import FrameType
from typing import Any, Final

_TERMINATION_SIGNALS: Final = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
_SignalHandler = Callable[[int, FrameType | None], Any] | int | None


class TerminationRequested(BaseException):
    """Propagate service cancellation after the child process is reaped."""


class termination_guard(AbstractContextManager[None]):
    """Turn service termination signals into a cleanup-safe exception."""

    def __init__(self) -> None:
        self._previous: dict[signal.Signals, _SignalHandler] = {}
        self._active = False

    def __enter__(self) -> None:
        if threading.current_thread() is not threading.main_thread():
            return
        self._active = True
        for requested_signal in _TERMINATION_SIGNALS:
            self._previous[requested_signal] = signal.getsignal(requested_signal)
            signal.signal(requested_signal, self._handle)

    def __exit__(self, *args: object) -> None:
        if not self._active:
            return
        for requested_signal, previous in self._previous.items():
            signal.signal(requested_signal, previous)

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        del frame
        for requested_signal in self._previous:
            signal.signal(requested_signal, signal.SIG_IGN)
        raise TerminationRequested(signum)


class defer_termination(AbstractContextManager[None]):
    """Close the spawn-registration race before delivering a pending signal."""

    def __init__(self) -> None:
        self._previous_mask: set[int | signal.Signals] = set()

    def __enter__(self) -> None:
        self._previous_mask = signal.pthread_sigmask(
            signal.SIG_BLOCK,
            _TERMINATION_SIGNALS,
        )

    def __exit__(self, *args: object) -> None:
        signal.pthread_sigmask(signal.SIG_SETMASK, self._previous_mask)


def unblock_termination_signals() -> None:
    """Activate handlers after an exec inherited the spawn-time signal mask."""
    signal.pthread_sigmask(signal.SIG_UNBLOCK, _TERMINATION_SIGNALS)


def terminate_process_group(
    process: subprocess.Popen[bytes], grace_seconds: float
) -> None:
    """Terminate the entire child session without an unbounded wait."""
    _signal_group(process.pid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while process_group_exists(process.pid) and time.monotonic() < deadline:
        process.poll()
        time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
    if process_group_exists(process.pid):
        _signal_group(process.pid, signal.SIGKILL)
    _reap_direct_child(process, grace_seconds)
    if process.stdout is not None:
        process.stdout.close()


def terminate_safely(process: subprocess.Popen[bytes], grace_seconds: float) -> None:
    """Best-effort cleanup used from every failure and cancellation path."""
    try:
        terminate_process_group(process, grace_seconds)
    except BaseException:
        _signal_group(process.pid, signal.SIGKILL)
        try:
            process.kill()
        except OSError:
            pass
        _reap_direct_child(process, grace_seconds)
        if process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass


def process_group_exists(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_group(pid: int, requested_signal: signal.Signals) -> None:
    try:
        os.killpg(pid, requested_signal)
    except ProcessLookupError:
        pass


def _reap_direct_child(process: subprocess.Popen[bytes], timeout: float) -> None:
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
