from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID


class RecoveryRepository(Protocol):
    async def recover_stale_queued(
        self,
        now: datetime,
        stale_before: datetime,
        *,
        limit: int = 100,
    ) -> tuple[UUID, ...]: ...

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
    queued_stale_after: timedelta = timedelta(seconds=60)

    def __post_init__(self) -> None:
        if (
            self.interval <= 0
            or not 1 <= self.batch_size <= 1000
            or self.queued_stale_after <= timedelta(0)
        ):
            raise ValueError("invalid recovery settings")


class DownloadRecoverySweeper:
    def __init__(
        self,
        repository: RecoveryRepository,
        clock: Callable[[], datetime],
        settings: RecoverySettings | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._settings = settings or RecoverySettings()

    async def tick(
        self,
    ) -> tuple[tuple[UUID, ...], tuple[UUID, ...], tuple[UUID, ...]]:
        now = self._clock()
        queued = await self._repository.recover_stale_queued(
            now,
            now - self._settings.queued_stale_after,
            limit=self._settings.batch_size,
        )
        stale = await self._repository.reclaim_stale(
            now, limit=self._settings.batch_size
        )
        ready = await self._repository.release_ready_retries(
            now, limit=self._settings.batch_size
        )
        return queued, stale, ready

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._settings.interval)
            except TimeoutError:
                continue
