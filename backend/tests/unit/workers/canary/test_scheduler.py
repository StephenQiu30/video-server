from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryStage,
)
from app.runner.provider_registry import provider_profile
from app.workers.canary.scheduler import ProviderCanaryScheduler
from app.workers.canary.targets import ProviderCanaryTarget

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)
URL = "https://vimeo.com/76979871"
PROFILE_VERSION = provider_profile(URL).version
CONTEXT = ProviderAccessContextRef(
    provider_key="vimeo",
    profile_version=PROFILE_VERSION,
    access_mode=ProviderAccessMode.ANONYMOUS,
    credential_version_id=None,
    egress_affinity_id="default:0123456789ab",
    client_profile_id="yt-dlp-default",
    attestation_provider_version=None,
    engine_commit="current-engine",
)


class Repository:
    def __init__(self, checked: dict[ProviderCanaryStage, datetime | None]) -> None:
        self.checked = checked

    async def latest_checked_at(
        self,
        target_id: str,
        profile_version: str,
        stage: ProviderCanaryStage,
        access_mode: ProviderAccessMode,
        engine_commit: str,
        egress_affinity_id: str,
        client_profile_id: str,
        context_generation_id: str,
    ) -> datetime | None:
        assert target_id == "vimeo-owned-1"
        assert profile_version == PROFILE_VERSION
        assert access_mode is ProviderAccessMode.ANONYMOUS
        assert (engine_commit, egress_affinity_id, client_profile_id) in {
            (
                CONTEXT.engine_commit,
                CONTEXT.egress_affinity_id,
                CONTEXT.client_profile_id,
            ),
            ("unresolved", "unresolved", "unresolved"),
        }
        assert context_generation_id in {CONTEXT.generation_id, "unresolved"}
        return self.checked[stage]


class Service:
    def __init__(self, *, context_error: Exception | None = None) -> None:
        self.context_error = context_error
        self.executed: list[
            tuple[
                ProviderCanaryStage,
                ProviderAccessContextRef | None,
                Exception | None,
            ]
        ] = []

    async def context_for(
        self, target: ProviderCanaryTarget
    ) -> ProviderAccessContextRef:
        assert target.provider_key == "vimeo"
        if self.context_error is not None:
            raise self.context_error
        return CONTEXT

    async def execute(
        self,
        target: ProviderCanaryTarget,
        *,
        expected_context: ProviderAccessContextRef | None = None,
        context_error: Exception | None = None,
    ) -> None:
        self.executed.append((target.stage, expected_context, context_error))


def target(stage: ProviderCanaryStage) -> ProviderCanaryTarget:
    return ProviderCanaryTarget(
        target_id="vimeo-owned-1",
        provider_key="vimeo",
        stage=stage,
        access_mode=ProviderAccessMode.ANONYMOUS,
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

    assert service.executed == [(ProviderCanaryStage.METADATA, CONTEXT, None)]


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

    assert service.executed == [(ProviderCanaryStage.MEDIA, CONTEXT, None)]


@pytest.mark.asyncio
async def test_recent_unresolved_failure_throttles_runner_outage() -> None:
    repository = Repository(
        {
            ProviderCanaryStage.METADATA: NOW,
            ProviderCanaryStage.MEDIA: NOW,
        }
    )
    service = Service(context_error=RuntimeError("runner offline"))
    scheduler = ProviderCanaryScheduler(
        repository,  # type: ignore[arg-type]
        service,  # type: ignore[arg-type]
        (target(ProviderCanaryStage.METADATA),),
        metadata_interval=timedelta(hours=6),
        media_interval=timedelta(hours=24),
        poll_seconds=60,
        now=lambda: NOW,
    )

    await scheduler.run_due()

    assert service.executed == []


@pytest.mark.asyncio
async def test_due_runner_outage_is_recorded_without_guessed_context() -> None:
    repository = Repository(
        {
            ProviderCanaryStage.METADATA: None,
            ProviderCanaryStage.MEDIA: None,
        }
    )
    service = Service(context_error=RuntimeError("runner offline"))
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

    assert len(service.executed) == 1
    stage, context, context_error = service.executed[0]
    assert stage is ProviderCanaryStage.MEDIA
    assert context is None
    assert isinstance(context_error, RuntimeError)
