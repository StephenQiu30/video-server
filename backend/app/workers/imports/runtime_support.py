from __future__ import annotations

import asyncio
import hashlib
import os
import signal
import socket
from datetime import UTC, datetime


def worker_id() -> str:
    hostname = socket.gethostname()
    digest = hashlib.sha256(hostname.encode()).hexdigest()[:12]
    return f"import-{hostname[:64]}-{digest}-{os.getpid()}"


def utc_now() -> datetime:
    return datetime.now(UTC)


def install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for requested_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(requested_signal, stop.set)
        except NotImplementedError:
            pass
