from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.application.downloads import EncryptedUrl
from app.application.provider_analysis_canary import (
    AnalysisCanaryEvidence,
    AnalysisCanaryObject,
    AnalysisCanaryTarget,
    ProviderAnalysisCanaryService,
)
from app.domain.providers import (
    ProviderAccessContextRef,
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
)

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)
URL = "https://www.acfun.cn/v/ac35457073"
TARGET = AnalysisCanaryTarget(
    "acfun-owned-1",
    "acfun",
    "acfun-public-v1",
    "default",
    "yt-dlp-default",
    URL,
)


class Reader:
    def __init__(self, evidence: AnalysisCanaryEvidence | None) -> None:
        self.evidence = evidence

    async def get(
        self, analysis_job_id: UUID, *, now: datetime
    ) -> AnalysisCanaryEvidence | None:
        assert analysis_job_id.version == 4
        assert now == NOW
        return self.evidence


class Writer:
    def __init__(self) -> None:
        self.saved: list[ProviderCanaryResult] = []

    async def save(self, result: ProviderCanaryResult) -> None:
        self.saved.append(result)


class Decryptor:
    def __init__(self, url: str) -> None:
        self.url = url

    def decrypt(self, envelope: EncryptedUrl) -> str:
        assert envelope.key_id == "fernet-v1"
        return self.url


class Storage:
    async def stat(self, object_key: str):
        assert object_key == "downloads/video.mp4"
        return type("Stat", (), {"size_bytes": 1_024, "sha256": "b" * 64})()


def evidence() -> AnalysisCanaryEvidence:
    return AnalysisCanaryEvidence(
        EncryptedUrl(b"ciphertext", b"nonce", "fernet-v1"),
        ProviderAccessContextRef(
            provider_key="acfun",
            profile_version="acfun-public-v1",
            access_mode=ProviderAccessMode.ANONYMOUS,
            credential_version_id=None,
            egress_affinity_id="default",
            client_profile_id="yt-dlp-default",
            attestation_provider_version=None,
            engine_commit="5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc",
        ),
        NOW,
        (AnalysisCanaryObject("downloads/video.mp4", 1_024, "b" * 64),),
    )


@pytest.mark.asyncio
async def test_attests_matching_persisted_full_video_evidence() -> None:
    writer = Writer()
    service = ProviderAnalysisCanaryService(
        Reader(evidence()),
        writer,
        Decryptor(URL),
        Storage(),
        now=lambda: NOW,
        timer=lambda: 1.0,
    )

    result = await service.attest(TARGET, uuid4())

    assert result.stage is ProviderCanaryStage.ANALYSIS
    assert result.outcome is ProviderCanaryOutcome.SUCCEEDED
    assert result.stable_error_code is None
    assert writer.saved == [result]


@pytest.mark.asyncio
async def test_source_mismatch_persists_only_a_stable_failure_code() -> None:
    writer = Writer()
    service = ProviderAnalysisCanaryService(
        Reader(evidence()),
        writer,
        Decryptor("https://www.acfun.cn/v/ac999"),
        Storage(),
        now=lambda: NOW,
        timer=lambda: 1.0,
    )

    result = await service.attest(TARGET, uuid4())

    assert result.outcome is ProviderCanaryOutcome.FAILED
    assert result.stable_error_code == "analysis_evidence_invalid"
    assert URL not in repr(result)
