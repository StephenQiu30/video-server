from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)
from app.infrastructure.database.models import (
    ArtifactRow,
    DownloadJobRow,
    MediaInspectionRow,
)
from app.infrastructure.provider_status_evidence import (
    MergedProviderStatusEvidenceReader,
    _download_result,
)

NOW = datetime(2026, 8, 29, 4, tzinfo=UTC)


class Reader:
    def __init__(self, *results: ProviderCanaryResult) -> None:
        self._results = results

    async def list_recent(
        self, *, limit_per_provider: int
    ) -> dict[str, tuple[ProviderCanaryResult, ...]]:
        assert limit_per_provider > 0
        return {"tiktok": self._results} if self._results else {}


def evidence(minutes: int) -> ProviderCanaryResult:
    return ProviderCanaryResult(
        target_id=f"target:{minutes}",
        provider_key="tiktok",
        profile_version="tiktok-web-v1",
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

    results = await reader.list_recent(limit_per_provider=3)

    assert [item.checked_at for item in results["tiktok"]] == [
        NOW,
        NOW - timedelta(minutes=10),
        NOW - timedelta(minutes=20),
    ]


def test_projects_verified_download_without_exposing_source_url() -> None:
    context = ProviderAccessContextRef(
        provider_key="tiktok",
        profile_version="tiktok-web-v1",
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
