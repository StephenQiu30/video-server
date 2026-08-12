from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.domain.providers import (
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.database import Base, create_session_factory
from app.infrastructure.provider_canary_repository import (
    SqlAlchemyProviderCanaryRepository,
)
from sqlalchemy.ext.asyncio import create_async_engine

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)


def canary(provider: str, age: int) -> ProviderCanaryResult:
    return ProviderCanaryResult(
        target_id=f"{provider}-owned-1",
        provider_key=provider,
        profile_version=f"{provider}-public-v1",
        stage=ProviderCanaryStage.METADATA,
        access_mode=ProviderAccessMode.ANONYMOUS,
        outcome=ProviderCanaryOutcome.SUCCEEDED,
        stable_error_code=None,
        checked_at=NOW - timedelta(minutes=age),
        duration_ms=100,
        engine_commit="5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc",
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
    )


@pytest.mark.asyncio
async def test_persists_sanitized_evidence_and_limits_each_provider() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    repository = SqlAlchemyProviderCanaryRepository(create_session_factory(engine))
    for age in range(6):
        await repository.save(canary("vimeo", age))
    for age in range(2):
        await repository.save(canary("youtube", age))

    recent = await repository.list_recent(limit_per_provider=5)
    latest = await repository.latest_checked_at(
        "vimeo-owned-1", ProviderCanaryStage.METADATA
    )

    assert len(recent["vimeo"]) == 5
    assert len(recent["youtube"]) == 2
    assert recent["vimeo"][0].checked_at == NOW
    assert latest == NOW
    await engine.dispose()
