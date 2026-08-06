from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.analysis import (
    AnalysisApplicationError,
    AnalysisApplicationErrorCode,
    AnalysisCreate,
    AnalysisJobSnapshot,
    AnalyzeAndPublish,
)
from app.domain.analysis import Transcript, TranscriptSegment
from tests.unit.application.analysis.fakes import (
    FakeAnalyzer,
    FakeRepository,
    published_result,
)
from tests.unit.domain.analysis.test_result_validation import document

NOW = datetime(2026, 8, 6, 8, tzinfo=UTC)
JOB_ID = UUID("22222222-2222-4222-8222-222222222222")


def transcript() -> Transcript:
    return Transcript(
        (
            TranscriptSegment("s1", 0, 1_000, "zh-CN", "第一段。"),
            TranscriptSegment("s2", 1_000, 2_000, "en-US", "Second segment."),
            TranscriptSegment("s3", 2_000, 3_000, "zh-CN", "第三段。"),
        )
    )


def running_job() -> AnalysisJobSnapshot:
    command = AnalysisCreate(
        id=JOB_ID,
        artifact_id=UUID("11111111-1111-4111-8111-111111111111"),
        owner_hash="a" * 64,
        idempotency_key="request",
        request_fingerprint="fingerprint",
        input_sha256="b" * 64,
        profile="standard-v1",
        schema_version="analysis.v1",
        output_language="zh-CN",
        max_attempts=3,
        outbox_event_id=UUID("33333333-3333-4333-8333-333333333333"),
        outbox_event_type="analysis.requested",
    )
    return replace(
        AnalysisJobSnapshot.queued(command, now=NOW),
        status="running",
        stage="validating",
        progress=90,
        attempt=1,
        version=4,
        lease_owner="worker-a",
        lease_expires_at=NOW + timedelta(seconds=30),
        heartbeat_at=NOW,
    )


@pytest.mark.asyncio
async def test_analyzer_protocol_output_is_validated_and_published_atomically() -> None:
    repository = FakeRepository()
    repository.jobs[JOB_ID] = running_job()
    analyzer = FakeAnalyzer(document())
    publish = AnalyzeAndPublish(
        repository=repository, analyzer=analyzer, now=lambda: NOW
    )

    result = await publish(JOB_ID, "worker-a", transcript())

    assert result == published_result(repository)
    assert analyzer.calls[0][1] == "zh-CN"
    command = repository.published[0]
    assert command.expected_version == 4
    assert command.lease_owner == "worker-a"
    assert repository.jobs[JOB_ID].status == "succeeded"


@pytest.mark.asyncio
async def test_extra_model_fields_are_rejected_without_partial_publish() -> None:
    repository = FakeRepository()
    repository.jobs[JOB_ID] = running_job()
    payload = document()
    payload["model_commentary"] = "I ignored the requested JSON schema"
    analyzer = FakeAnalyzer(payload)
    publish = AnalyzeAndPublish(
        repository=repository, analyzer=analyzer, now=lambda: NOW
    )

    with pytest.raises(AnalysisApplicationError) as caught:
        await publish(JOB_ID, "worker-a", transcript())

    assert caught.value.code is AnalysisApplicationErrorCode.INVALID_MODEL_OUTPUT
    assert repository.published == []
    assert repository.jobs[JOB_ID].status == "running"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "job,owner",
    [
        (replace(running_job(), status="queued", stage=None), "worker-a"),
        (replace(running_job(), lease_owner="worker-b"), "worker-a"),
        (replace(running_job(), lease_expires_at=NOW), "worker-a"),
    ],
)
async def test_publish_requires_active_validating_lease(
    job: AnalysisJobSnapshot, owner: str
) -> None:
    repository = FakeRepository()
    repository.jobs[JOB_ID] = job
    analyzer = FakeAnalyzer(document())
    publish = AnalyzeAndPublish(
        repository=repository, analyzer=analyzer, now=lambda: NOW
    )

    with pytest.raises(AnalysisApplicationError) as caught:
        await publish(JOB_ID, owner, transcript())

    assert caught.value.code is AnalysisApplicationErrorCode.INVALID_STATE
    assert analyzer.calls == []


@pytest.mark.asyncio
async def test_missing_job_is_not_found_and_provider_failure_is_stable() -> None:
    repository = FakeRepository()
    analyzer = FakeAnalyzer(document())
    publish = AnalyzeAndPublish(
        repository=repository, analyzer=analyzer, now=lambda: NOW
    )
    with pytest.raises(AnalysisApplicationError) as missing:
        await publish(JOB_ID, "worker-a", transcript())
    assert missing.value.code is AnalysisApplicationErrorCode.NOT_FOUND

    class BrokenAnalyzer:
        async def analyze(self, transcript: Transcript, output_language: str) -> object:
            del transcript, output_language
            raise TimeoutError

    repository.jobs[JOB_ID] = running_job()
    broken = AnalyzeAndPublish(
        repository=repository,
        analyzer=BrokenAnalyzer(),
        now=lambda: NOW,
    )
    with pytest.raises(AnalysisApplicationError) as provider:
        await broken(JOB_ID, "worker-a", transcript())
    assert provider.value.code is AnalysisApplicationErrorCode.PROVIDER_FAILURE
    assert repository.published == []
