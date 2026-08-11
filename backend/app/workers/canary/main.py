"""Run with: python -m app.workers.canary.main."""

from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import Settings, get_settings_for_role
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.media_runner import MediaRunnerHttpClient, MediaRunnerRouter
from app.infrastructure.provider_canary_repository import (
    SqlAlchemyProviderCanaryRepository,
)
from app.workers.canary.scheduler import ProviderCanaryScheduler
from app.workers.canary.service import ProviderCanaryService
from app.workers.canary.targets import parse_canary_targets
from app.workers.download.workspace import SharedWorkspaceCleaner
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class ProviderCanaryRuntime:
    scheduler: ProviderCanaryScheduler
    runner: MediaRunnerRouter
    engine: AsyncEngine

    async def close(self) -> None:
        try:
            await self.runner.close()
        finally:
            await self.engine.dispose()


def build_runtime(settings: Settings) -> ProviderCanaryRuntime:
    engine = create_engine(settings.database_url)
    repository = SqlAlchemyProviderCanaryRepository(create_session_factory(engine))
    anonymous = MediaRunnerHttpClient(
        base_url=settings.runner_base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
    operator = (
        MediaRunnerHttpClient(
            base_url=settings.runner_operator_base_url,
            secret=settings.runner_hmac_secret.get_secret_value().encode(),
            workspace_root=settings.runner_workspace_root,
            inspect_timeout_seconds=settings.inspect_timeout_seconds,
            download_timeout_seconds=settings.download_timeout_seconds,
        )
        if settings.runner_operator_base_url is not None
        else None
    )
    runner = MediaRunnerRouter(anonymous, operator)
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
