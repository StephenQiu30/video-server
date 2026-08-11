from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta

from app.domain.providers import ProviderCanaryStage
from app.workers.canary.service import CanaryRepository, ProviderCanaryService
from app.workers.canary.targets import ProviderCanaryTarget


class ProviderCanaryScheduler:
    def __init__(
        self,
        repository: CanaryRepository,
        service: ProviderCanaryService,
        targets: tuple[ProviderCanaryTarget, ...],
        *,
        metadata_interval: timedelta,
        media_interval: timedelta,
        poll_seconds: float,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._service = service
        self._targets = targets
        self._metadata_interval = metadata_interval
        self._media_interval = media_interval
        self._poll_seconds = poll_seconds
        self._now = now

    async def run_due(self) -> None:
        for target in self._targets:
            latest = await self._repository.latest_checked_at(
                target.target_id, target.stage
            )
            interval = (
                self._metadata_interval
                if target.stage is ProviderCanaryStage.METADATA
                else self._media_interval
            )
            if latest is None or self._now() - latest >= interval:
                await self._service.execute(target)

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await self.run_due()
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                pass
