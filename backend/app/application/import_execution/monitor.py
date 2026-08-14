from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from .errors import ImportExecutionUnavailable, ImportLeaseLost


async def monitored[ResultT](
    operation: Callable[[], Coroutine[Any, Any, ResultT]],
    heartbeat: Callable[[], Awaitable[None]],
    *,
    interval: float,
) -> ResultT:
    await heartbeat()
    task = asyncio.create_task(operation())
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval)
            if done:
                return await task
            await heartbeat()
    except (ImportLeaseLost, ImportExecutionUnavailable, asyncio.CancelledError):
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise
