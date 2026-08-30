"""Delete explicitly retired report artifacts and quarantined orphan objects."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.infrastructure.analysis_report_lifecycle import (
    AnalysisReportLifecycleRepository,
    ReportPurgeResult,
)
from app.infrastructure.object_storage import MinioObjectStorage

_log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReportLifecycleResult:
    artifacts: ReportPurgeResult
    orphans_deleted: int


class ReportLifecycleWorker:
    def __init__(
        self,
        repository: AnalysisReportLifecycleRepository,
        storage: MinioObjectStorage,
        clock: Callable[[], datetime],
        *,
        interval: float,
        batch_size: int,
        orphan_grace: timedelta,
        delete_timeout: float,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._clock = clock
        self._interval = interval
        self._batch_size = batch_size
        self._orphan_grace = orphan_grace
        self._delete_timeout = delete_timeout

    async def _delete(self, object_key: str) -> None:
        await asyncio.wait_for(
            self._storage.delete(object_key), timeout=self._delete_timeout
        )

    async def tick(self) -> ReportLifecycleResult:
        now = self._clock()
        artifacts = await self._repository.purge_report_artifacts(
            now, self._delete, limit=self._batch_size
        )
        expected = await self._repository.expected_report_object_keys()
        cutoff = now - self._orphan_grace
        deleted = 0
        for item in await self._storage.list("analyses/"):
            if deleted >= self._batch_size:
                break
            if item.object_key in expected or item.last_modified > cutoff:
                continue
            await self._delete(item.object_key)
            deleted += 1
        return ReportLifecycleResult(artifacts, deleted)

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self.tick()
            except Exception:
                _log.exception("analysis report lifecycle sweep failed")
            try:
                await asyncio.wait_for(stop.wait(), self._interval)
            except TimeoutError:
                continue
