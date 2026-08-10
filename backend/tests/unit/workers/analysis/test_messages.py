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


def requested_body(
    *, event_type: str = "analysis.requested"
) -> tuple[bytes, UUID, UUID]:
    job_id = uuid4()
    run_id = uuid4()
    envelope = EventEnvelope(
        schema_version=1,
        event_id=uuid4(),
        aggregate_id=job_id,
        event_type=event_type,
        occurred_at=NOW,
        payload={
            "job_id": str(job_id),
            "run_id": str(run_id),
            "run_no": 1,
            "version": 0,
        },
    )
    return envelope.to_bytes(), job_id, run_id


class FakeDelivery:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.redelivered = False
        self.acked = 0
        self.nacked: list[bool] = []

    async def ack(self) -> None:
        self.acked += 1

    async def nack(self, *, requeue: bool) -> None:
        self.nacked.append(requeue)


class FakeHandler:
    def __init__(self, disposition: AnalysisDisposition) -> None:
        self.disposition = disposition
        self.calls: list[tuple[UUID, UUID, int, int]] = []

    async def execute(
        self, job_id: UUID, run_id: UUID, run_no: int, version: int
    ) -> AnalysisDisposition:
        self.calls.append((job_id, run_id, run_no, version))
        return self.disposition


def test_analysis_message_is_strict_and_identity_bound() -> None:
    body, job_id, run_id = requested_body()
    requested = parse_analysis_requested(body)
    assert requested.job_id == job_id
    assert (requested.run_id, requested.run_no, requested.version) == (run_id, 1, 0)

    wrong_type, _, _ = requested_body(event_type="download.requested")
    with pytest.raises(AnalysisMessageError):
        parse_analysis_requested(wrong_type)
    with pytest.raises(AnalysisMessageError):
        parse_analysis_requested(b"not-json")


@pytest.mark.asyncio
async def test_delivery_ack_requeue_and_dead_letters_bad_messages() -> None:
    body, job_id, run_id = requested_body()
    accepted = FakeDelivery(body)
    handler = FakeHandler(AnalysisDisposition.ACK)
    await process_delivery(accepted, handler)
    assert accepted.acked == 1
    assert handler.calls == [(job_id, run_id, 1, 0)]

    retried = FakeDelivery(body)
    await process_delivery(retried, FakeHandler(AnalysisDisposition.REQUEUE))
    assert retried.nacked == [True]

    poison = FakeDelivery(body)
    poison.redelivered = True
    await process_delivery(poison, FakeHandler(AnalysisDisposition.REQUEUE))
    assert poison.nacked == [False]

    rejected = FakeDelivery(b"bad")
    await process_delivery(rejected, handler)
    assert rejected.nacked == [False]
