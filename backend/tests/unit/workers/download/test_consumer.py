from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.application.download_execution import ExecutionDisposition
from app.infrastructure.messaging import EventEnvelope
from app.workers.download.consumer import process_delivery


class FakeDelivery:
    def __init__(self, body: bytes, *, redelivered: bool = False) -> None:
        self.body = body
        self.redelivered = redelivered
        self.acked = 0
        self.nacked: list[bool] = []

    async def ack(self) -> None:
        self.acked += 1

    async def nack(self, *, requeue: bool) -> None:
        self.nacked.append(requeue)


class FakeHandler:
    def __init__(self, result=ExecutionDisposition.ACK) -> None:
        self.result = result
        self.error: Exception | None = None

    async def execute(self, job_id):
        if self.error is not None:
            raise self.error
        return self.result


def body() -> bytes:
    job_id = uuid4()
    return EventEnvelope(
        schema_version=1,
        event_id=uuid4(),
        aggregate_id=job_id,
        event_type="download.requested",
        occurred_at=datetime.now(UTC),
        payload={"job_id": str(job_id), "attempt": 0, "version": 0},
    ).to_bytes()


@pytest.mark.asyncio
async def test_consumer_acks_only_converged_execution() -> None:
    success = FakeDelivery(body())
    await process_delivery(success, FakeHandler())
    assert (success.acked, success.nacked) == (1, [])

    retry = FakeDelivery(body())
    await process_delivery(retry, FakeHandler(ExecutionDisposition.REQUEUE))
    assert (retry.acked, retry.nacked) == (0, [True])


@pytest.mark.asyncio
async def test_consumer_dead_letters_bad_contract_and_requeues_faults() -> None:
    invalid = FakeDelivery(b"not-json")
    await process_delivery(invalid, FakeHandler())
    assert invalid.nacked == [False]

    transient = FakeDelivery(body())
    handler = FakeHandler()
    handler.error = OSError("database unavailable")
    await process_delivery(transient, handler)
    assert transient.nacked == [True]

    poison = FakeDelivery(body(), redelivered=True)
    await process_delivery(poison, handler)
    assert poison.nacked == [False]
