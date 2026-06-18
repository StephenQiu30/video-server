"""Centralized single-service runtime.

Runs the FastAPI API server and an embedded RQ queue consumer in one process.
The API server runs on the main thread; the RQ worker runs on a daemon thread.

Usage:
    python -m app.runtime
"""

from __future__ import annotations

import logging
import os
import signal
import threading

logger = logging.getLogger(__name__)

# Global flag for health checks to verify the queue consumer is alive.
_worker_ready: bool = False
_worker_thread: threading.Thread | None = None


def _run_worker() -> None:
    """Entry point for the RQ worker daemon thread."""
    global _worker_ready
    try:
        from worker.main import main as worker_main
        _worker_ready = True
        logger.info("Queue consumer thread started")
        worker_main()
    except Exception:
        logger.exception("Queue consumer thread exited with error")
    finally:
        _worker_ready = False


def _start_worker_thread() -> threading.Thread:
    """Start the RQ worker in a daemon thread and return the thread reference."""
    thread = threading.Thread(target=_run_worker, name="rq-worker", daemon=True)
    thread.start()
    return thread


def main() -> None:
    """Start the centralized runtime: API server + queue consumer."""
    global _worker_thread

    import uvicorn

    from app.core.config import get_settings

    settings = get_settings()

    _worker_thread = _start_worker_thread()

    host = os.getenv("API_HOST", settings.api_host)
    port = int(os.getenv("API_PORT", str(settings.api_port)))

    logger.info("Starting centralized runtime on %s:%s", host, port)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
