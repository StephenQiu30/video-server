"""Recover report publications whose broker delivery or lease was lost."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID


class RecoveryRepository(Protocol):
    async def recover_pending(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]: ...


class ReportRecoverySweeper:
    def __init__(
        self,
        repository: RecoveryRepository,
        clock: Callable[[], datetime],
        *,
        interval: float = 5,
        batch_size: int = 100,
    ) -> None:
        if interval <= 0 or not 1 <= batch_size <= 1000:
            raise ValueError("invalid report recovery settings")
        self._repository = repository
        self._clock = clock
        self._interval = interval
        self._batch_size = batch_size

    async def tick(self) -> tuple[UUID, ...]:
        return await self._repository.recover_pending(
            self._clock(), limit=self._batch_size
        )

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop.wait(), self._interval)
            except TimeoutError:
                continue
