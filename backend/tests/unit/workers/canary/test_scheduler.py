from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.providers import ProviderCanaryStage
from app.workers.canary.scheduler import ProviderCanaryScheduler
from app.workers.canary.targets import ProviderCanaryTarget

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)
URL = "https://vimeo.com/76979871"


class Repository:
    def __init__(self, checked: dict[ProviderCanaryStage, datetime | None]) -> None:
        self.checked = checked

    async def latest_checked_at(
        self, target_id: str, stage: ProviderCanaryStage
    ) -> datetime | None:
        assert target_id == "vimeo-owned-1"
        return self.checked[stage]


class Service:
    def __init__(self) -> None:
        self.executed: list[ProviderCanaryStage] = []

    async def execute(self, target: ProviderCanaryTarget) -> None:
        self.executed.append(target.stage)


def target(stage: ProviderCanaryStage) -> ProviderCanaryTarget:
    return ProviderCanaryTarget(
        target_id="vimeo-owned-1",
        provider_key="vimeo",
        stage=stage,
        url=URL,
    )


@pytest.mark.asyncio
async def test_runs_only_targets_whose_stage_interval_is_due() -> None:
    repository = Repository(
        {
            ProviderCanaryStage.METADATA: NOW - timedelta(hours=7),
            ProviderCanaryStage.MEDIA: NOW - timedelta(hours=23),
        }
    )
    service = Service()
    scheduler = ProviderCanaryScheduler(
        repository,  # type: ignore[arg-type]
        service,  # type: ignore[arg-type]
        (
            target(ProviderCanaryStage.METADATA),
            target(ProviderCanaryStage.MEDIA),
        ),
        metadata_interval=timedelta(hours=6),
        media_interval=timedelta(hours=24),
        poll_seconds=60,
        now=lambda: NOW,
    )

    await scheduler.run_due()

    assert service.executed == [ProviderCanaryStage.METADATA]


@pytest.mark.asyncio
async def test_never_checked_targets_are_due() -> None:
    repository = Repository(
        {
            ProviderCanaryStage.METADATA: None,
            ProviderCanaryStage.MEDIA: None,
        }
    )
    service = Service()
    scheduler = ProviderCanaryScheduler(
        repository,  # type: ignore[arg-type]
        service,  # type: ignore[arg-type]
        (target(ProviderCanaryStage.MEDIA),),
        metadata_interval=timedelta(hours=6),
        media_interval=timedelta(hours=24),
        poll_seconds=60,
        now=lambda: NOW,
    )

    await scheduler.run_due()

    assert service.executed == [ProviderCanaryStage.MEDIA]
