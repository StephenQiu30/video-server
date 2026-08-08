"""Bounded artifact retention cleanup for the download worker."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.infrastructure.database import ArtifactPurgeResult


class ArtifactRepository(Protocol):
    async def purge_expired_artifacts(
        self,
        now: datetime,
        delete: Callable[[str], Awaitable[None]],
        *,
        limit: int,
    ) -> ArtifactPurgeResult: ...


@dataclass(frozen=True, slots=True)
class ArtifactCleanupSettings:
    interval: float = 300.0
    batch_size: int = 50
    delete_timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.interval <= 0 or not 1 <= self.batch_size <= 200:
            raise ValueError("invalid artifact cleanup settings")
        if self.delete_timeout <= 0:
            raise ValueError("artifact delete timeout must be positive")


class ArtifactGarbageCollector:
    def __init__(
        self,
        repository: ArtifactRepository,
        delete: Callable[[str], Awaitable[None]],
        clock: Callable[[], datetime],
        settings: ArtifactCleanupSettings | None = None,
    ) -> None:
        self._repository = repository
        self._delete = delete
        self._clock = clock
        self._settings = settings or ArtifactCleanupSettings()

    async def tick(self) -> ArtifactPurgeResult:
        async def delete_with_timeout(object_key: str) -> None:
            await asyncio.wait_for(
                self._delete(object_key), timeout=self._settings.delete_timeout
            )

        return await self._repository.purge_expired_artifacts(
            self._clock(), delete_with_timeout, limit=self._settings.batch_size
        )

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
