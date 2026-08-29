from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.application.provider_canaries import ProviderEvidenceScope
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.database import create_session_factory
from app.infrastructure.database.models import (
    ArtifactRow,
    DownloadJobRow,
    MediaFormatRow,
    MediaInspectionRow,
)
from app.infrastructure.provider_status_evidence import (
    MergedProviderStatusEvidenceReader,
    SqlAlchemyDownloadEvidenceReader,
    _download_result,
)
from sqlalchemy.ext.asyncio import AsyncEngine

NOW = datetime(2026, 8, 29, 4, tzinfo=UTC)


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


def evidence(minutes: int) -> ProviderCanaryResult:
    return ProviderCanaryResult(
        target_id=f"target:{minutes}",
        provider_key="tiktok",
        profile_version="tiktok-public-player-v2",
        stage=ProviderCanaryStage.MEDIA,
        access_mode=ProviderAccessMode.OPERATOR_MANAGED,
        outcome=ProviderCanaryOutcome.SUCCEEDED,
        checked_at=NOW - timedelta(minutes=minutes),
        duration_ms=100,
        engine_commit="engine",
        egress_affinity_id="default",
        client_profile_id="chrome",
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
    anonymous = replace(
        evidence(33),
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
    )
    job = DownloadJobRow(
        id=uuid4(),
        started_at=NOW - timedelta(seconds=2),
        finished_at=NOW,
        created_at=NOW - timedelta(seconds=3),
    )
    artifact = ArtifactRow(created_at=NOW)
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


async def _seed_download(
    sessions,
    *,
    age: int,
    access_mode: ProviderAccessMode,
    job_id: UUID | None = None,
) -> ProviderCanaryResult:
    inspection_id, format_id = uuid4(), uuid4()
    job_id = job_id or uuid4()
    completed_at = NOW - timedelta(minutes=age)
    operator = access_mode is ProviderAccessMode.OPERATOR_MANAGED
    context = ProviderAccessContextRef(
        provider_key="tiktok",
        profile_version="tiktok-public-player-v3",
        access_mode=access_mode,
        credential_version_id="operator-v1" if operator else None,
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
        attestation_provider_version=None,
        engine_commit="engine",
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
        session.add(
            DownloadJobRow(
                id=job_id,
                inspection_id=inspection_id,
                format_id=format_id,
                owner_hash="a" * 64,
                idempotency_key=f"download-{job_id}",
                request_fingerprint="d" * 64,
                semantic_plan={"height": 720},
                status="succeeded",
                progress=100,
                attempt=1,
                started_at=completed_at - timedelta(seconds=2),
                finished_at=completed_at,
                created_at=completed_at - timedelta(seconds=3),
                updated_at=completed_at,
            )
        )
        await session.flush()
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
            media_metadata={"video_streams": 1, "audio_streams": 1},
            created_at=completed_at,
        )
        session.add(artifact)
    result = _download_result(
        DownloadJobRow(
            id=job_id,
            started_at=completed_at - timedelta(seconds=2),
            finished_at=completed_at,
            created_at=completed_at - timedelta(seconds=3),
        ),
        ArtifactRow(created_at=completed_at),
        MediaInspectionRow(
            metadata_json={"provider_access_context": context.to_document()}
        ),
    )
    assert result is not None
    return result
