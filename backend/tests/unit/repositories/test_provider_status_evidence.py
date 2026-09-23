from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.core.db import create_session_factory
from app.models import ArtifactRow, DownloadJobRow, MediaFormatRow, MediaInspectionRow
from app.repositories.providers.status_evidence import (
    MergedProviderStatusEvidenceReader,
    SqlAlchemyDownloadEvidenceReader,
    _download_result,
)
from app.services.provider_canaries import (
    ProviderEvidenceScope as _ProviderEvidenceScope,
)
from app.services.provider_types import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

NOW = datetime(2026, 8, 29, 4, tzinfo=UTC)


def runtime_context(
    *,
    profile_version: str,
    access_mode: ProviderAccessMode,
    engine_commit: str = "engine",
    client_profile_id: str | None = None,
    credential_version_id: str | None = None,
    attestation_provider_version: str | None = None,
) -> ProviderAccessContextRef:
    operator = access_mode is ProviderAccessMode.OPERATOR_MANAGED
    if operator and credential_version_id is None:
        credential_version_id = "operator-current"
    if access_mode is ProviderAccessMode.GUEST and credential_version_id is None:
        credential_version_id = "guest-current"
    return ProviderAccessContextRef(
        provider_key="tiktok",
        profile_version=profile_version,
        access_mode=access_mode,
        credential_version_id=credential_version_id,
        egress_affinity_id="default",
        client_profile_id=(
            client_profile_id
            or (
                "chrome"
                if profile_version == "tiktok-public-player-v2"
                else "yt-dlp-default"
            )
        ),
        attestation_provider_version=attestation_provider_version,
        engine_commit=engine_commit,
        runtime_revision="a" * 64,
    )


def ProviderEvidenceScope(  # noqa: N802
    *,
    profile_version: str,
    access_mode: ProviderAccessMode,
    engine_commit: str = "engine",
    runtime_revision: str = "a" * 64,
) -> _ProviderEvidenceScope:
    return _ProviderEvidenceScope(
        profile_version=profile_version,
        access_context=replace(
            runtime_context(
                profile_version=profile_version,
                access_mode=access_mode,
                engine_commit=engine_commit,
            ),
            runtime_revision=runtime_revision,
        ),
    )


class Reader:
    def __init__(self, *results: ProviderCanaryResult) -> None:
        self._results = results

    async def list_recent(
        self,
        *,
        limit_per_provider_stage: int,
        scopes: Mapping[str, ProviderEvidenceScope],
    ) -> dict[str, tuple[ProviderCanaryResult, ...]]:
        assert limit_per_provider_stage > 0
        return {"tiktok": self._results} if self._results else {}


def evidence(
    minutes: int,
    *,
    access_mode: ProviderAccessMode = ProviderAccessMode.OPERATOR_MANAGED,
    engine_commit: str = "engine",
) -> ProviderCanaryResult:
    context = runtime_context(
        profile_version="tiktok-public-player-v2",
        access_mode=access_mode,
        engine_commit=engine_commit,
    )
    return ProviderCanaryResult(
        target_id=f"target:{minutes}",
        provider_key="tiktok",
        profile_version="tiktok-public-player-v2",
        stage=ProviderCanaryStage.MEDIA,
        access_mode=access_mode,
        outcome=ProviderCanaryOutcome.SUCCEEDED,
        checked_at=NOW - timedelta(minutes=minutes),
        duration_ms=100,
        engine_commit=engine_commit,
        egress_affinity_id="default",
        client_profile_id="chrome",
        context_generation_id=context.generation_id,
    )


@pytest.mark.asyncio
async def test_merges_orders_and_limits_evidence_sources() -> None:
    reader = MergedProviderStatusEvidenceReader(
        Reader(evidence(30), evidence(10)),
        Reader(evidence(20), evidence(0)),
    )

    results = await reader.list_recent(
        limit_per_provider_stage=3,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v2",
                access_mode=ProviderAccessMode.OPERATOR_MANAGED,
            )
        },
    )

    assert [item.checked_at for item in results["tiktok"]] == [
        NOW,
        NOW - timedelta(minutes=10),
        NOW - timedelta(minutes=20),
    ]


@pytest.mark.asyncio
async def test_filters_scope_before_merged_reader_limit() -> None:
    disabled_operator = tuple(evidence(index) for index in range(32))
    anonymous = evidence(
        33,
        access_mode=ProviderAccessMode.ANONYMOUS,
    )
    reader = MergedProviderStatusEvidenceReader(
        Reader(*disabled_operator, anonymous),
    )

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v2",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert results["tiktok"] == (anonymous,)


@pytest.mark.asyncio
async def test_merged_reader_breaks_equal_timestamp_ties_deterministically() -> None:
    first = replace(evidence(0), target_id="target:a")
    last = replace(evidence(0), target_id="target:z")
    reader = MergedProviderStatusEvidenceReader(Reader(first), Reader(last))

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v2",
                access_mode=ProviderAccessMode.OPERATOR_MANAGED,
            )
        },
    )

    assert results["tiktok"] == (last,)


@pytest.mark.asyncio
async def test_merged_reader_limits_each_stage_independently() -> None:
    newest_media = evidence(0)
    older_media = evidence(1)
    metadata = replace(evidence(2), stage=ProviderCanaryStage.METADATA)
    reader = MergedProviderStatusEvidenceReader(
        Reader(newest_media, older_media, metadata)
    )

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v2",
                access_mode=ProviderAccessMode.OPERATOR_MANAGED,
            )
        },
    )

    assert results["tiktok"] == (newest_media, metadata)


@pytest.mark.asyncio
async def test_download_reader_filters_scope_before_per_provider_limit(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    for age in range(32):
        await _seed_download(
            sessions,
            age=age,
            access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        )
    expected = await _seed_download(
        sessions,
        age=33,
        access_mode=ProviderAccessMode.ANONYMOUS,
    )
    reader = SqlAlchemyDownloadEvidenceReader(sessions)

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert results == {"tiktok": (expected,)}


@pytest.mark.asyncio
async def test_download_reader_filters_engine_before_provider_limit(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    for age in range(32):
        await _seed_download(
            sessions,
            age=age,
            access_mode=ProviderAccessMode.ANONYMOUS,
            engine_commit="previous-engine",
        )
    expected = await _seed_download(
        sessions,
        age=33,
        access_mode=ProviderAccessMode.ANONYMOUS,
        engine_commit="current-engine",
    )
    reader = SqlAlchemyDownloadEvidenceReader(sessions)

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
                engine_commit="current-engine",
            )
        },
    )

    assert results == {"tiktok": (expected,)}


@pytest.mark.asyncio
async def test_download_reader_uses_actual_context_after_legacy_job_migration(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    expected = await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.ANONYMOUS,
        execution_revision="b" * 64,
    )
    reader = SqlAlchemyDownloadEvidenceReader(sessions)

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
                runtime_revision="b" * 64,
            )
        },
    )

    assert results == {"tiktok": (expected,)}


@pytest.mark.asyncio
async def test_download_reader_keeps_failed_attempt_in_current_runner_scope(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    expected = await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.ANONYMOUS,
        status="failed",
        error_code="provider_verification_failed",
        execution_revision="b" * 64,
    )
    results = await SqlAlchemyDownloadEvidenceReader(sessions).list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
                runtime_revision="b" * 64,
            )
        },
    )
    assert results == {"tiktok": (expected,)}


@pytest.mark.asyncio
async def test_download_reader_skips_guest_rotation_before_media_io(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    seeded = await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.GUEST,
        status="failed",
        error_code="provider_session_expired",
        execution_revision="b" * 64,
    )
    job_id = UUID(seeded.target_id.removeprefix("download:"))
    async with sessions() as session, session.begin():
        job = await session.get(DownloadJobRow, job_id)
        assert job is not None
        job.error_code = "provider_guest_context_required"
    results = await SqlAlchemyDownloadEvidenceReader(sessions).list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.GUEST,
                runtime_revision="b" * 64,
            )
        },
    )
    assert results == {}


@pytest.mark.asyncio
async def test_download_reader_ignores_context_from_previous_attempt_after_rollback(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    old_result = await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.ANONYMOUS,
        execution_revision="b" * 64,
    )
    job_id = UUID(old_result.target_id.removeprefix("download:"))
    async with sessions() as session, session.begin():
        job = await session.get(DownloadJobRow, job_id)
        artifact = await session.scalar(
            select(ArtifactRow).where(ArtifactRow.job_id == job_id)
        )
        assert job is not None and artifact is not None
        inspection = await session.get(MediaInspectionRow, job.inspection_id)
        assert inspection is not None
        planned = dict(inspection.metadata_json["provider_access_context"])
        planned["runtime_revision"] = "b" * 64
        inspection.metadata_json = {"provider_access_context": planned}
        job.attempt = 2
        artifact.attempt = 2
        artifact.media_metadata = {"video_streams": 1, "audio_streams": 1}

    reader = SqlAlchemyDownloadEvidenceReader(sessions)
    stale = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
                runtime_revision="b" * 64,
            )
        },
    )
    legacy = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
                runtime_revision="a" * 64,
            )
        },
    )
    assert stale == {}
    assert legacy == {}


@pytest.mark.asyncio
async def test_download_reader_breaks_equal_timestamp_ties_by_job_id(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.ANONYMOUS,
        job_id=UUID(int=1),
    )
    expected = await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.ANONYMOUS,
        job_id=UUID(int=2),
    )
    reader = SqlAlchemyDownloadEvidenceReader(sessions)

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert results == {"tiktok": (expected,)}


@pytest.mark.asyncio
async def test_download_reader_includes_terminal_failures(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = create_session_factory(postgres_engine)
    expected = await _seed_download(
        sessions,
        age=0,
        access_mode=ProviderAccessMode.ANONYMOUS,
        status="failed",
        error_code="provider_session_expired",
    )
    reader = SqlAlchemyDownloadEvidenceReader(sessions)

    results = await reader.list_recent(
        limit_per_provider_stage=1,
        scopes={
            "tiktok": ProviderEvidenceScope(
                profile_version="tiktok-public-player-v3",
                access_mode=ProviderAccessMode.ANONYMOUS,
            )
        },
    )

    assert results == {"tiktok": (expected,)}
    assert expected.outcome is ProviderCanaryOutcome.FAILED
    assert expected.stable_error_code == "provider_session_expired"


def test_projects_verified_download_without_exposing_source_url() -> None:
    context = ProviderAccessContextRef(
        provider_key="tiktok",
        profile_version="tiktok-public-player-v2",
        access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        credential_version_id="browser-live",
        egress_affinity_id="default",
        client_profile_id="chrome",
        attestation_provider_version=None,
        engine_commit="engine",
        runtime_revision="a" * 64,
    )
    job = DownloadJobRow(
        id=uuid4(),
        status="succeeded",
        attempt=1,
        execution_access_context=context.to_document(),
        execution_context_attempt=1,
        started_at=NOW - timedelta(seconds=2),
        finished_at=NOW,
        created_at=NOW - timedelta(seconds=3),
    )
    artifact = ArtifactRow(created_at=NOW, attempt=1)
    inspection = MediaInspectionRow(
        metadata_json={"provider_access_context": context.to_document()}
    )

    result = _download_result(job, artifact, inspection)

    assert result is not None
    assert result.target_id == f"download:{job.id}"
    assert result.provider_key == "tiktok"
    assert result.stage is ProviderCanaryStage.MEDIA
    assert result.duration_ms == 2000
    assert result.stable_error_code is None


def test_projects_terminal_download_failure_with_stable_error_code() -> None:
    context = ProviderAccessContextRef(
        provider_key="tiktok",
        profile_version="tiktok-public-player-v2",
        access_mode=ProviderAccessMode.ANONYMOUS,
        credential_version_id=None,
        egress_affinity_id="default",
        client_profile_id="chrome",
        attestation_provider_version=None,
        engine_commit="engine",
        runtime_revision="a" * 64,
    )
    job = DownloadJobRow(
        id=uuid4(),
        status="failed",
        attempt=1,
        execution_access_context=context.to_document(),
        execution_context_attempt=1,
        error_code="provider_link_unavailable",
        started_at=NOW - timedelta(seconds=2),
        finished_at=NOW,
        created_at=NOW - timedelta(seconds=3),
    )
    inspection = MediaInspectionRow(
        metadata_json={"provider_access_context": context.to_document()}
    )

    result = _download_result(job, None, inspection)

    assert result is not None
    assert result.outcome is ProviderCanaryOutcome.FAILED
    assert result.stable_error_code == "provider_link_unavailable"


async def _seed_download(
    sessions,
    *,
    age: int,
    access_mode: ProviderAccessMode,
    job_id: UUID | None = None,
    engine_commit: str = "engine",
    status: str = "succeeded",
    error_code: str | None = None,
    execution_revision: str | None = None,
) -> ProviderCanaryResult:
    inspection_id, format_id = uuid4(), uuid4()
    job_id = job_id or uuid4()
    completed_at = NOW - timedelta(minutes=age)
    operator = access_mode is ProviderAccessMode.OPERATOR_MANAGED
    context = ProviderAccessContextRef(
        provider_key="tiktok",
        profile_version="tiktok-public-player-v3",
        access_mode=access_mode,
        credential_version_id=(
            "operator-current"
            if operator
            else "guest-current"
            if access_mode is ProviderAccessMode.GUEST
            else None
        ),
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit=engine_commit,
        runtime_revision="a" * 64,
    )
    execution_context = (
        replace(context, runtime_revision=execution_revision)
        if execution_revision is not None
        else context
    )
    async with sessions() as session, session.begin():
        session.add(
            MediaInspectionRow(
                id=inspection_id,
                owner_hash="a" * 64,
                idempotency_key=f"inspection-{inspection_id}",
                request_fingerprint="b" * 64,
                url_ciphertext=b"ciphertext",
                url_nonce=b"nonce",
                url_key_id="primary",
                extractor_key="TikTok",
                provider_media_id=f"video-{inspection_id}",
                title="TikTok public sample",
                duration_seconds=2,
                metadata_json={"provider_access_context": context.to_document()},
                expires_at=NOW + timedelta(days=1),
                created_at=completed_at,
            )
        )
        await session.flush()
        session.add(
            MediaFormatRow(
                id=format_id,
                inspection_id=inspection_id,
                display_name="720p",
                plan_fingerprint="c" * 64,
                semantic_plan={"height": 720},
                provider_hints={},
                expires_at=NOW + timedelta(days=1),
                created_at=completed_at,
            )
        )
        await session.flush()
        job = DownloadJobRow(
            id=job_id,
            inspection_id=inspection_id,
            format_id=format_id,
            owner_hash="a" * 64,
            idempotency_key=f"download-{job_id}",
            request_fingerprint="d" * 64,
            semantic_plan={"height": 720},
            execution_access_context=execution_context.to_document(),
            execution_context_attempt=1,
            status=status,
            progress=100 if status == "succeeded" else 0,
            attempt=1,
            started_at=completed_at - timedelta(seconds=2),
            finished_at=completed_at if status in {"succeeded", "failed"} else None,
            error_code=error_code,
            created_at=completed_at - timedelta(seconds=3),
            updated_at=completed_at,
        )
        session.add(job)
        await session.flush()
        if status == "succeeded":
            artifact = ArtifactRow(
                id=uuid4(),
                job_id=job_id,
                attempt=1,
                bucket="video-artifacts",
                object_key=f"downloads/{job_id}/1/video.mp4",
                sha256="e" * 64,
                size_bytes=1024,
                duration_ms=2000,
                container="mp4",
                content_type="video/mp4",
                media_metadata={
                    "video_streams": 1,
                    "audio_streams": 1,
                    "execution_access_context": execution_context.to_document(),
                },
                created_at=completed_at,
            )
            session.add(artifact)
    result = _download_result(
        DownloadJobRow(
            id=job_id,
            status=status,
            attempt=1,
            execution_access_context=execution_context.to_document(),
            execution_context_attempt=1,
            error_code=error_code,
            started_at=completed_at - timedelta(seconds=2),
            finished_at=completed_at,
            created_at=completed_at - timedelta(seconds=3),
        ),
        (
            ArtifactRow(
                created_at=completed_at,
                attempt=1,
                media_metadata={
                    "execution_access_context": execution_context.to_document()
                },
            )
            if status == "succeeded"
            else None
        ),
        MediaInspectionRow(
            metadata_json={"provider_access_context": context.to_document()}
        ),
    )
    assert result is not None
    return result
