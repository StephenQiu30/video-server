"""Fail unless every registered Provider has current verified status."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from app.application.provider_canaries import ProviderStatusService
from app.core.config import get_settings_for_role
from app.domain.providers import ProviderSupportStatus
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.media_runner import MediaRunnerHttpClient, MediaRunnerRouter
from app.infrastructure.provider_canary_repository import (
    SqlAlchemyProviderCanaryRepository,
)
from app.infrastructure.provider_status import configured_provider_statuses
from app.runner.provider_registry import configure_provider_instances


async def pending_provider_statuses() -> tuple[dict[str, str], ...]:
    settings = get_settings_for_role("provider-canary")
    configure_provider_instances(settings.peertube_allowed_instances)
    engine = create_engine(settings.database_url)
    anonymous_runner = MediaRunnerHttpClient(
        base_url=settings.runner_base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
    runner = MediaRunnerRouter(
        anonymous_runner,
        {
            provider: MediaRunnerHttpClient(
                base_url=base_url,
                secret=settings.runner_hmac_secret.get_secret_value().encode(),
                workspace_root=settings.runner_workspace_root,
                inspect_timeout_seconds=settings.inspect_timeout_seconds,
                download_timeout_seconds=settings.download_timeout_seconds,
            )
            for provider, base_url in settings.runner_operator_base_urls.items()
        },
    )
    service = ProviderStatusService(
        SqlAlchemyProviderCanaryRepository(create_session_factory(engine)),
        configured_provider_statuses(frozenset(settings.runner_operator_base_urls)),
        now=lambda: datetime.now(UTC),
        context_reader=runner,
        approved_keys=settings.provider_verified_keys,
    )
    try:
        views = await service.list()
    finally:
        await runner.close()
        await engine.dispose()
    return tuple(
        {"key": item.key, "status": item.status.value}
        for item in views
        if item.registered and item.status is not ProviderSupportStatus.VERIFIED
    )


async def _run() -> int:
    pending = await pending_provider_statuses()
    print(
        json.dumps(
            {"archive_ready": not pending, "pending": pending},
            separators=(",", ":"),
        )
    )
    return 0 if not pending else 1


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
