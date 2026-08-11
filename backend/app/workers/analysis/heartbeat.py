"""Periodic worker capability heartbeat."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Protocol


class WorkerRegistry(Protocol):
    async def heartbeat(
        self,
        worker_id: str,
        *,
        app_version: str,
        message_schema_version: int,
        now: datetime,
    ) -> None: ...

    async def unregister(self, worker_id: str) -> None: ...


class AnalysisWorkerHeartbeat:
    def __init__(
        self,
        registry: WorkerRegistry,
        *,
        worker_id: str,
        app_version: str,
        message_schema_version: int,
        interval: float,
        clock: Callable[[], datetime],
    ) -> None:
        if not worker_id or not app_version or message_schema_version <= 0:
            raise ValueError("invalid analysis worker heartbeat identity")
        if interval <= 0:
            raise ValueError("analysis worker heartbeat interval must be positive")
        self._registry = registry
        self._worker_id = worker_id
        self._app_version = app_version
        self._message_schema_version = message_schema_version
        self._interval = interval
        self._clock = clock

    async def tick(self) -> None:
        await self._registry.heartbeat(
            self._worker_id,
            app_version=self._app_version,
            message_schema_version=self._message_schema_version,
            now=self._clock(),
        )

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await self.tick()
            try:
                await asyncio.wait_for(stop.wait(), self._interval)
            except TimeoutError:
                continue

    async def close(self) -> None:
        await self._registry.unregister(self._worker_id)
