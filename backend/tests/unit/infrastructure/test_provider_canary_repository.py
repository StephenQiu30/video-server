from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.provider_canaries import (
    ProviderEvidenceScope as _ProviderEvidenceScope,
)
from app.domain.providers import (
    ProviderAccessContextRef,
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
from app.runner.version import YTDLP_ENGINE_COMMIT
from sqlalchemy.ext.asyncio import AsyncEngine

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)


def runtime_context(
    provider: str,
    *,
    profile_version: str,
    access_mode: ProviderAccessMode,
    engine_commit: str = YTDLP_ENGINE_COMMIT,
    egress_affinity_id: str = "default",
    client_profile_id: str = "yt-dlp-default",
) -> ProviderAccessContextRef:
    operator = access_mode is ProviderAccessMode.OPERATOR_MANAGED
    return ProviderAccessContextRef(
        provider_key=provider,
        profile_version=profile_version,
        access_mode=access_mode,
        credential_version_id="operator-current" if operator else None,
        egress_affinity_id=egress_affinity_id,
        client_profile_id=client_profile_id,
        attestation_provider_version=None,
        engine_commit=engine_commit,
    )


def ProviderEvidenceScope(  # noqa: N802
    *,
    profile_version: str,
    access_mode: ProviderAccessMode,
    engine_commit: str = YTDLP_ENGINE_COMMIT,
    egress_affinity_id: str = "default",
    client_profile_id: str = "yt-dlp-default",
) -> _ProviderEvidenceScope:
    provider = profile_version.split("-public", maxsplit=1)[0]
    return _ProviderEvidenceScope(
        profile_version=profile_version,
        access_context=runtime_context(
            provider,
            profile_version=profile_version,
            access_mode=access_mode,
            engine_commit=engine_commit,
            egress_affinity_id=egress_affinity_id,
            client_profile_id=client_profile_id,
        ),
    )


def canary(
    provider: str,
    age: int,
    *,
    access_mode: ProviderAccessMode = ProviderAccessMode.ANONYMOUS,
    stage: ProviderCanaryStage = ProviderCanaryStage.METADATA,
    profile_version: str | None = None,
    engine_commit: str = YTDLP_ENGINE_COMMIT,
    egress_affinity_id: str = "default",
    client_profile_id: str = "yt-dlp-default",
) -> ProviderCanaryResult:
    profile_version = profile_version or f"{provider}-public"
    context = runtime_context(
        provider,
        profile_version=profile_version,
        access_mode=access_mode,
        engine_commit=engine_commit,
        egress_affinity_id=egress_affinity_id,
        client_profile_id=client_profile_id,
    )
    return ProviderCanaryResult(
        target_id=f"{provider}-owned-1",
        provider_key=provider,
        profile_version=profile_version,
        stage=stage,
        access_mode=access_mode,
        outcome=ProviderCanaryOutcome.SUCCEEDED,
        stable_error_code=None,
        checked_at=NOW - timedelta(minutes=age),
        duration_ms=100,
        engine_commit=engine_commit,
        egress_affinity_id=egress_affinity_id,
        client_profile_id=client_profile_id,
        context_generation_id=context.generation_id,
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
                profile_version=f"{provider}-public",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
            for provider in ("vimeo", "youtube")
        },
    )
    latest = await repository.latest_checked_at(
        "vimeo-owned-1",
        "vimeo-public",
        ProviderCanaryStage.METADATA,
        ProviderAccessMode.ANONYMOUS,
        canary("vimeo", 0).engine_commit,
        canary("vimeo", 0).egress_affinity_id,
        canary("vimeo", 0).client_profile_id,
        canary("vimeo", 0).context_generation_id,
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
                profile_version="vimeo-public",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert recent == {"vimeo": (expected,)}


@pytest.mark.asyncio
async def test_filters_engine_before_per_provider_limit(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    for age in range(32):
        await repository.save(canary("vimeo", age, engine_commit="previous-engine"))
    expected = canary("vimeo", 33)
    await repository.save(expected)

    recent = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public",
                access_mode=ProviderAccessMode.ANONYMOUS,
                engine_commit=YTDLP_ENGINE_COMMIT,
            )
        },
    )

    assert recent == {"vimeo": (expected,)}


@pytest.mark.asyncio
async def test_filters_context_generation_before_per_provider_limit(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    for age in range(32):
        await repository.save(
            replace(
                canary("vimeo", age),
                context_generation_id="stale-generation",
            )
        )
    expected = canary("vimeo", 33)
    await repository.save(expected)

    recent = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public",
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
                profile_version="vimeo-public",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )
    operator = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public",
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
                profile_version="vimeo-public",
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
        expected.engine_commit,
        expected.egress_affinity_id,
        expected.client_profile_id,
        expected.context_generation_id,
    )

    assert latest == expected.checked_at


@pytest.mark.asyncio
async def test_latest_target_check_is_scoped_to_profile_version(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    old = canary("vimeo", 0, profile_version="vimeo-public")
    await repository.save(old)

    latest = await repository.latest_checked_at(
        old.target_id,
        "vimeo-public-v2",
        old.stage,
        old.access_mode,
        old.engine_commit,
        old.egress_affinity_id,
        old.client_profile_id,
        old.context_generation_id,
    )

    assert latest is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("engine_commit", "egress_affinity_id", "client_profile_id"),
    (
        ("next-engine", "default", "yt-dlp-default"),
        (
            YTDLP_ENGINE_COMMIT,
            "provider:vimeo:0123456789ab",
            "yt-dlp-default",
        ),
        (
            YTDLP_ENGINE_COMMIT,
            "default",
            "vimeo-web-v2",
        ),
    ),
)
async def test_latest_target_check_is_scoped_to_runtime_generation(
    postgres_engine: AsyncEngine,
    engine_commit: str,
    egress_affinity_id: str,
    client_profile_id: str,
) -> None:
    repository = SqlAlchemyProviderCanaryRepository(
        create_session_factory(postgres_engine)
    )
    previous = canary("vimeo", 0)
    await repository.save(previous)

    latest = await repository.latest_checked_at(
        previous.target_id,
        previous.profile_version,
        previous.stage,
        previous.access_mode,
        engine_commit,
        egress_affinity_id,
        client_profile_id,
        previous.context_generation_id,
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
                    profile_version="vimeo-public",
                    stage=ProviderCanaryStage.METADATA.value,
                    access_mode=ProviderAccessMode.ANONYMOUS.value,
                    outcome=ProviderCanaryOutcome.SUCCEEDED.value,
                    stable_error_code=None,
                    checked_at=NOW,
                    duration_ms=100,
                    engine_commit="engine",
                    egress_affinity_id="default",
                    client_profile_id="yt-dlp-default",
                    context_generation_id=runtime_context(
                        "vimeo",
                        profile_version="vimeo-public",
                        access_mode=ProviderAccessMode.ANONYMOUS,
                        engine_commit="engine",
                    ).generation_id,
                )
            )
    repository = SqlAlchemyProviderCanaryRepository(sessions)

    recent = await repository.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "vimeo": ProviderEvidenceScope(
                profile_version="vimeo-public",
                access_mode=ProviderAccessMode.ANONYMOUS,
                engine_commit="engine",
            )
        },
    )

    assert recent["vimeo"][0].target_id == "target:z"
