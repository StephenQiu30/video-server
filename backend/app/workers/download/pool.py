"""Bounded asynchronous worker pool for download deliveries."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class AsyncWorkerPool[T]:
    """Run a bounded number of async jobs without growing local backlog."""

    def __init__(
        self,
        processor: Callable[[T], Awaitable[None]],
        *,
        workers: int,
        drain_timeout: float = 60.0,
    ) -> None:
        if workers < 1:
            raise ValueError("worker count must be positive")
        self._processor = processor
        self._workers = workers
        self._drain_timeout = drain_timeout
        self._queue: asyncio.Queue[T | None] = asyncio.Queue(maxsize=workers)
        self._tasks: tuple[asyncio.Task[None], ...] = ()
        self._started = False
        self._closed = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._tasks = tuple(
            asyncio.create_task(self._run_worker(), name=f"download-pool-{index}")
            for index in range(self._workers)
        )

    async def submit(self, item: T) -> None:
        if not self._started or self._closed:
            raise RuntimeError("worker pool is not accepting jobs")
        # Backpressure is intentional. RabbitMQ keeps the delivery unacked while
        # the local pool is full, so work is not silently dropped in process memory.
        await self._queue.put(item)

    async def close(self) -> None:
        if not self._started or self._closed:
            return
        self._closed = True

        # Drain accepted deliveries before stopping workers. The consumer is
        # cancelled by its owner before this method is called. The drain is
        # bounded so a hung processor cannot block process shutdown forever;
        # a timed-out delivery is still unacked, so RabbitMQ returns it to the
        # queue when the channel closes and a healthy worker retries it.
        try:
            async with asyncio.timeout(self._drain_timeout):
                await self._queue.join()
        except TimeoutError:
            for task in self._tasks:
                task.cancel()
        else:
            for _ in self._tasks:
                await self._queue.put(None)
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = ()

    async def _run_worker(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                if item is None:
                    return
                await self._processor(item)
            finally:
                self._queue.task_done()
