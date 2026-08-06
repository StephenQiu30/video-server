from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine
from pathlib import Path
from typing import Any


class WorkspaceLimitExceeded(RuntimeError):
    pass


async def run_with_workspace_limit[ResultT](
    operation: Coroutine[Any, Any, ResultT],
    *,
    root: Path,
    max_bytes: int,
    poll_interval_seconds: float,
) -> ResultT:
    process_task = asyncio.create_task(operation)
    monitor_task = asyncio.create_task(_monitor(root, max_bytes, poll_interval_seconds))
    try:
        done, _ = await asyncio.wait(
            {process_task, monitor_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if monitor_task in done:
            failure = monitor_task.exception()
            if failure is not None:
                raise failure
        return await process_task
    except BaseException:
        if not process_task.done():
            process_task.cancel()
        await asyncio.gather(process_task, return_exceptions=True)
        raise
    finally:
        if not monitor_task.done():
            monitor_task.cancel()
        await asyncio.gather(monitor_task, return_exceptions=True)


async def _monitor(root: Path, max_bytes: int, interval: float) -> None:
    while True:
        exceeded = await asyncio.to_thread(_exceeds_limit, root, max_bytes)
        if exceeded:
            raise WorkspaceLimitExceeded
        await asyncio.sleep(interval)


def _exceeds_limit(root: Path, max_bytes: int) -> bool:
    total = 0
    try:
        for directory, _, files in os.walk(root, followlinks=False):
            base = Path(directory)
            for name in files:
                try:
                    total += (base / name).lstat().st_size
                except FileNotFoundError:
                    continue
                if total > max_bytes:
                    return True
    except OSError:
        return True
    return False
