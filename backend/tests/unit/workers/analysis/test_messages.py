from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.application.analysis_execution import AnalysisDisposition
from app.infrastructure.messaging import EventEnvelope
from app.workers.analysis.consumer import process_delivery
from app.workers.analysis.message import (
    AnalysisMessageError,
    parse_analysis_requested,
)

from .fakes import NOW


def requested_body(*, event_type: str = "analysis.requested") -> tuple[bytes, UUID]:
    job_id = uuid4()
    artifact_id = uuid4()
    envelope = EventEnvelope(
        schema_version=1,
        event_id=uuid4(),
        aggregate_id=job_id,
        event_type=event_type,
        occurred_at=NOW,
        payload={
            "job_id": str(job_id),
            "artifact_id": str(artifact_id),
            "input_sha256": "a" * 64,
            "profile": "default",
            "schema_version": "analysis.v1",
            "output_language": "zh-CN",
            "attempt": 0,
            "version": 0,
        },
    )
    return envelope.to_bytes(), job_id


class FakeDelivery:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.acked = 0
        self.nacked: list[bool] = []

    async def ack(self) -> None:
        self.acked += 1

    async def nack(self, *, requeue: bool) -> None:
        self.nacked.append(requeue)


class FakeHandler:
    def __init__(self, disposition: AnalysisDisposition) -> None:
        self.disposition = disposition
        self.calls: list[UUID] = []

    async def execute(self, job_id: UUID) -> AnalysisDisposition:
        self.calls.append(job_id)
        return self.disposition


def test_analysis_message_is_strict_and_identity_bound() -> None:
    body, job_id = requested_body()
    requested = parse_analysis_requested(body)
    assert requested.job_id == job_id
    assert requested.attempt == 0

    wrong_type, _ = requested_body(event_type="download.requested")
    with pytest.raises(AnalysisMessageError):
        parse_analysis_requested(wrong_type)
    with pytest.raises(AnalysisMessageError):
        parse_analysis_requested(b"not-json")


@pytest.mark.asyncio
async def test_delivery_ack_requeue_and_dead_letters_bad_messages() -> None:
    body, job_id = requested_body()
    accepted = FakeDelivery(body)
    handler = FakeHandler(AnalysisDisposition.ACK)
    await process_delivery(accepted, handler)
    assert accepted.acked == 1
    assert handler.calls == [job_id]

    retried = FakeDelivery(body)
    await process_delivery(retried, FakeHandler(AnalysisDisposition.REQUEUE))
    assert retried.nacked == [True]

    rejected = FakeDelivery(b"bad")
    await process_delivery(rejected, handler)
    assert rejected.nacked == [False]
