from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


class RecoveryRepository(Protocol):
    async def reclaim_stale(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]: ...

    async def release_ready_retries(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[UUID, ...]: ...


@dataclass(frozen=True, slots=True)
class RecoverySettings:
    interval: float = 5.0
    batch_size: int = 100


class AnalysisRecoverySweeper:
    def __init__(
        self,
        repository: RecoveryRepository,
        clock: Callable[[], datetime],
        settings: RecoverySettings | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._settings = settings or RecoverySettings()
        if self._settings.interval <= 0 or not 1 <= self._settings.batch_size <= 1000:
            raise ValueError("invalid recovery settings")

    async def tick(self) -> tuple[tuple[UUID, ...], tuple[UUID, ...]]:
        stale = await self._repository.reclaim_stale(
            self._clock(), limit=self._settings.batch_size
        )
        ready = await self._repository.release_ready_retries(
            self._clock(), limit=self._settings.batch_size
        )
        return stale, ready

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop.wait(), self._settings.interval)
            except TimeoutError:
                continue
