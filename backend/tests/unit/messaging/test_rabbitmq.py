from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from aio_pika import DeliveryMode, ExchangeType
from app.infrastructure.messaging import (
    EventEnvelope,
    PublishNotConfirmed,
    RabbitMqPublisher,
    RabbitMqTopology,
)
from pamqp.commands import Basic


class FakeExchange:
    def __init__(self, confirmation=None) -> None:
        self.confirmation = confirmation or Basic.Ack()
        self.published = []

    async def publish(self, message, routing_key, *, mandatory, timeout):
        self.published.append((message, routing_key, mandatory, timeout))
        return self.confirmation


class FakeQueue:
    def __init__(self) -> None:
        self.bindings = []

    async def bind(self, exchange, routing_key):
        self.bindings.append((exchange, routing_key))


class FakeChannel:
    def __init__(self) -> None:
        self.main = FakeExchange()
        self.dead = FakeExchange()
        self.queue = FakeQueue()
        self.dead_queue = FakeQueue()
        self.exchange_calls = []
        self.queue_calls = []

    async def declare_exchange(self, name, kind, *, durable):
        self.exchange_calls.append((name, kind, durable))
        return self.dead if name.endswith(".dead") else self.main

    async def declare_queue(self, name, *, durable, arguments=None):
        self.queue_calls.append((name, durable, arguments))
        return self.dead_queue if name.endswith(".dead") else self.queue


class FakeConnection:
    def __init__(self) -> None:
        self.channel_value = FakeChannel()
        self.channel_calls = []
        self.closed = False

    async def channel(self, *, publisher_confirms, on_return_raises):
        self.channel_calls.append((publisher_confirms, on_return_raises))
        return self.channel_value

    async def close(self):
        self.closed = True


def event() -> EventEnvelope:
    return EventEnvelope(
        schema_version=1,
        event_id=uuid4(),
        aggregate_id=uuid4(),
        event_type="download.requested",
        occurred_at=datetime(2026, 8, 6, tzinfo=UTC),
        payload={"job_id": str(uuid4()), "attempt": 0, "version": 0},
    )


@pytest.mark.asyncio
async def test_robust_topology_and_confirmed_mandatory_publish(monkeypatch) -> None:
    connection = FakeConnection()

    async def connect(url, **kwargs):
        assert url == "amqp://broker/"
        assert kwargs["timeout"] == 10
        return connection

    monkeypatch.setattr(
        "app.infrastructure.messaging.rabbitmq.aio_pika.connect_robust", connect
    )
    topology = RabbitMqTopology("video.events", "video.download", "download.requested")
    publisher = RabbitMqPublisher("amqp://broker/", topology)
    await publisher.start()
    await publisher.publish(event())

    channel = connection.channel_value
    assert connection.channel_calls == [(True, True)]
    assert ("video.events", ExchangeType.TOPIC, True) in channel.exchange_calls
    assert ("video.events.dead", ExchangeType.DIRECT, True) in channel.exchange_calls
    queue_call = next(
        item for item in channel.queue_calls if item[0] == "video.download"
    )
    assert queue_call[1] is True
    assert queue_call[2] == {
        "x-dead-letter-exchange": "video.events.dead",
        "x-dead-letter-routing-key": "video.download.dead",
        "x-message-ttl": 1_800_000,
    }
    message, routing_key, mandatory, timeout = channel.main.published[0]
    assert (routing_key, mandatory, timeout) == ("download.requested", True, 10)
    assert message.delivery_mode is DeliveryMode.PERSISTENT
    assert message.message_id is not None
    await publisher.close()
    assert connection.closed


@pytest.mark.asyncio
async def test_nack_is_not_treated_as_success(monkeypatch) -> None:
    connection = FakeConnection()
    connection.channel_value.main.confirmation = Basic.Nack()

    async def connect(*args, **kwargs):
        return connection

    monkeypatch.setattr(
        "app.infrastructure.messaging.rabbitmq.aio_pika.connect_robust", connect
    )
    publisher = RabbitMqPublisher(
        "amqp://broker/",
        RabbitMqTopology("video.events", "video.download", "download.requested"),
    )
    await publisher.start()
    with pytest.raises(PublishNotConfirmed):
        await publisher.publish(event())


@pytest.mark.asyncio
async def test_topology_failure_closes_partial_connection(monkeypatch) -> None:
    connection = FakeConnection()

    async def fail_queue(*args, **kwargs):
        raise RuntimeError("topology declaration failed")

    connection.channel_value.declare_queue = fail_queue

    async def connect(*args, **kwargs):
        return connection

    monkeypatch.setattr(
        "app.infrastructure.messaging.rabbitmq.aio_pika.connect_robust", connect
    )
    publisher = RabbitMqPublisher(
        "amqp://broker/",
        RabbitMqTopology("video.events", "video.download", "download.requested"),
    )
    with pytest.raises(RuntimeError):
        await publisher.start()
    assert connection.closed
