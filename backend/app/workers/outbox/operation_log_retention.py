"""Periodically delete operation logs older than the configured retention."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol

_log = logging.getLogger(__name__)


class ExpiredOperationLogs(Protocol):
    async def purge_before(self, cutoff: datetime, *, limit: int) -> int: ...


class OperationLogRetention:
    def __init__(
        self,
        store: ExpiredOperationLogs,
        clock: Callable[[], datetime],
        *,
        retention: timedelta,
        interval: float,
        batch_size: int,
        max_batches: int = 20,
    ) -> None:
        self._store = store
        self._clock = clock
        self._retention = retention
        self._interval = interval
        self._batch_size = batch_size
        self._max_batches = max_batches

    async def tick(self) -> int:
        # Short batches keep each transaction small; any backlog left after
        # max_batches is drained by later ticks.
        cutoff = self._clock() - self._retention
        deleted = 0
        for _ in range(self._max_batches):
            count = await self._store.purge_before(cutoff, limit=self._batch_size)
            deleted += count
            if count < self._batch_size:
                break
        if deleted:
            _log.info("operation_log_retention_purged count=%d", deleted)
        return deleted

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                _log.exception("operation_log_retention_failed")
            try:
                await asyncio.wait_for(stop.wait(), self._interval)
            except TimeoutError:
                continue
