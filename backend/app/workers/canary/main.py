"""Run with: python -m app.workers.canary.main."""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import Settings, get_settings_for_role
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.media_runner_factory import (
    anonymous_media_runner,
    operator_media_runners,
)
from app.infrastructure.provider_canary_repository import (
    SqlAlchemyProviderCanaryRepository,
)
from app.runner.provider_registry import configure_provider_instances
from app.workers.canary.runner import ProviderCanaryRunner
from app.workers.canary.scheduler import ProviderCanaryScheduler
from app.workers.canary.service import ProviderCanaryService
from app.workers.canary.targets import parse_canary_targets
from app.workers.download.workspace import SharedWorkspaceCleaner
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class ProviderCanaryRuntime:
    scheduler: ProviderCanaryScheduler
    service: ProviderCanaryService
    runner: ProviderCanaryRunner
    engine: AsyncEngine

    async def close(self) -> None:
        try:
            await self.runner.close()
        finally:
            await self.engine.dispose()


def build_runtime(settings: Settings) -> ProviderCanaryRuntime:
    configure_provider_instances(settings.peertube_allowed_instances)
    engine = create_engine(settings.database_url)
    repository = SqlAlchemyProviderCanaryRepository(create_session_factory(engine))
    anonymous = anonymous_media_runner(settings)
    operators = operator_media_runners(settings)
    runner = ProviderCanaryRunner(anonymous, operators)
    service = ProviderCanaryService(
        repository,
        runner,
        SharedWorkspaceCleaner(settings.runner_workspace_root),
        now=_utc_now,
    )
    return ProviderCanaryRuntime(
        scheduler=ProviderCanaryScheduler(
            repository,
            service,
            parse_canary_targets(settings.provider_canary_targets),
            metadata_interval=timedelta(
                seconds=settings.provider_canary_metadata_interval_seconds
            ),
            media_interval=timedelta(
                seconds=settings.provider_canary_media_interval_seconds
            ),
            poll_seconds=settings.provider_canary_poll_seconds,
            now=_utc_now,
        ),
        service=service,
        runner=runner,
        engine=engine,
    )


async def run() -> None:
    runtime = build_runtime(get_settings_for_role("provider-canary"))
    stop = asyncio.Event()
    _install_signal_handlers(stop)
    try:
        await runtime.scheduler.run(stop)
    finally:
        await asyncio.shield(runtime.close())


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for requested_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(requested_signal, stop.set)
        except NotImplementedError:
            pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
