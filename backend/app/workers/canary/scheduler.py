from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta

from app.domain.providers import ProviderCanaryStage
from app.runner.provider_registry import provider_profile
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
            profile_version = provider_profile(target.safe_url()).version
            context = None
            context_error = None
            try:
                context = await self._service.context_for(target)
            except Exception as exc:
                context_error = exc
                # Persisted unresolved failures are throttled independently.
                # A recovered runner exposes its concrete generation and is
                # therefore due immediately without waiting for this cohort.
                latest = await self._repository.latest_checked_at(
                    target.target_id,
                    profile_version,
                    target.stage,
                    target.access_mode,
                    "unresolved",
                    "unresolved",
                    "unresolved",
                    "unresolved",
                )
            else:
                latest = await self._repository.latest_checked_at(
                    target.target_id,
                    profile_version,
                    target.stage,
                    target.access_mode,
                    context.engine_commit,
                    context.egress_affinity_id,
                    context.client_profile_id,
                    context.generation_id,
                )
            interval = (
                self._metadata_interval
                if target.stage is ProviderCanaryStage.METADATA
                else self._media_interval
            )
            if latest is None or self._now() - latest >= interval:
                await self._service.execute(
                    target,
                    expected_context=context,
                    context_error=context_error,
                )

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            await self.run_due()
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._poll_seconds)
            except TimeoutError:
                pass
