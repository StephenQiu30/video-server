from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.provider_canaries import ProviderEvidenceScope
from app.domain.providers import (
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.database import create_session_factory
from app.infrastructure.database.models import ProviderCanaryResultRow
from app.infrastructure.provider_canary_repository import (
    SqlAlchemyProviderCanaryRepository,
)
from sqlalchemy.ext.asyncio import AsyncEngine

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)


def canary(
    provider: str,
    age: int,
    *,
    access_mode: ProviderAccessMode = ProviderAccessMode.ANONYMOUS,
    stage: ProviderCanaryStage = ProviderCanaryStage.METADATA,
    profile_version: str | None = None,
) -> ProviderCanaryResult:
    return ProviderCanaryResult(
        target_id=f"{provider}-owned-1",
        provider_key=provider,
        profile_version=profile_version or f"{provider}-public-v1",
        stage=stage,
        access_mode=access_mode,
        outcome=ProviderCanaryOutcome.SUCCEEDED,
        stable_error_code=None,
        checked_at=NOW - timedelta(minutes=age),
        duration_ms=100,
        engine_commit="5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc",
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
    )


@pytest.mark.asyncio
async def test_persists_sanitized_evidence_and_limits_each_provider(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    for age in range(6):
        await repository.save(canary("vimeo", age))
    for age in range(2):
        await repository.save(canary("youtube", age))

    recent = await repository.list_recent(
        limit_per_provider_stage=5,
        scopes={
            provider: ProviderEvidenceScope(
                profile_version=f"{provider}-public-v1",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
            for provider in ("vimeo", "youtube")
        },
    )
    latest = await repository.latest_checked_at(
        "vimeo-owned-1",
        "vimeo-public-v1",
        ProviderCanaryStage.METADATA,
        ProviderAccessMode.ANONYMOUS,
    )

    assert len(recent["vimeo"]) == 5
    assert len(recent["youtube"]) == 2
    assert recent["vimeo"][0].checked_at == NOW
    assert latest == NOW


@pytest.mark.asyncio
async def test_filters_access_mode_before_per_provider_limit(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    for age in range(32):
        await repository.save(
            canary(
                "vimeo",
                age,
                access_mode=ProviderAccessMode.OPERATOR_MANAGED,
            )
        )
    expected = canary("vimeo", 33)
    await repository.save(expected)

    recent = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public-v1",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert recent == {"vimeo": (expected,)}


@pytest.mark.asyncio
async def test_public_failure_and_operator_success_are_read_in_separate_scopes(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    public_failure = replace(
        canary("vimeo", 1),
        outcome=ProviderCanaryOutcome.FAILED,
        stable_error_code="provider_auth_required",
    )
    operator_success = canary(
        "vimeo",
        0,
        access_mode=ProviderAccessMode.OPERATOR_MANAGED,
    )
    await repository.save(public_failure)
    await repository.save(operator_success)

    public = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public-v1",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )
    operator = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public-v1",
                access_mode=ProviderAccessMode.OPERATOR_MANAGED,
            )
        },
    )

    assert public == {"vimeo": (public_failure,)}
    assert operator == {"vimeo": (operator_success,)}


@pytest.mark.asyncio
async def test_limits_each_stage_independently(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    newest_metadata = canary("vimeo", 0)
    await repository.save(newest_metadata)
    await repository.save(canary("vimeo", 1))
    media = canary("vimeo", 2, stage=ProviderCanaryStage.MEDIA)
    await repository.save(media)

    recent = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public-v1",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert recent == {"vimeo": (newest_metadata, media)}


@pytest.mark.asyncio
async def test_latest_target_check_is_scoped_to_access_route(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    await repository.save(
        canary(
            "vimeo",
            0,
            access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        )
    )
    expected = canary("vimeo", 10)
    await repository.save(expected)

    latest = await repository.latest_checked_at(
        expected.target_id,
        expected.profile_version,
        expected.stage,
        ProviderAccessMode.ANONYMOUS,
    )

    assert latest == expected.checked_at


@pytest.mark.asyncio
async def test_latest_target_check_is_scoped_to_profile_version(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    old = canary("vimeo", 0, profile_version="vimeo-public-v1")
    await repository.save(old)

    latest = await repository.latest_checked_at(
        old.target_id,
        "vimeo-public-v2",
        old.stage,
        old.access_mode,
    )

    assert latest is None


@pytest.mark.asyncio
async def test_equal_timestamps_use_persisted_id_as_stable_tiebreaker(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    async with sessions() as session, session.begin():
        for row_id, target_id in ((UUID(int=1), "target:a"), (UUID(int=2), "target:z")):
            session.add(
                ProviderCanaryResultRow(
                    id=row_id,
                    target_id=target_id,
                    provider_key="vimeo",
                    profile_version="vimeo-public-v1",
                    stage=ProviderCanaryStage.METADATA.value,
                    access_mode=ProviderAccessMode.ANONYMOUS.value,
                    outcome=ProviderCanaryOutcome.SUCCEEDED.value,
                    stable_error_code=None,
                    checked_at=NOW,
                    duration_ms=100,
                    engine_commit="engine",
                    egress_affinity_id="default",
                    client_profile_id="yt-dlp-default",
                )
            )
    repository = SqlAlchemyProviderCanaryRepository(sessions)

    recent = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public-v1",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert recent["vimeo"][0].target_id == "target:z"
