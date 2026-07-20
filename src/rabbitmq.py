"""Direct RabbitMQ publisher/consumer contract for download jobs.

Only one durable direct exchange and queue are declared.  The body is the
versioned minimal contract ``{"job_id": "<uuid>"}``; business state remains in
PostgreSQL.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message


@dataclass(frozen=True, slots=True)
class RabbitMQTopology:
    exchange: str
    queue: str
    routing_key: str
    prefetch_count: int

    @classmethod
    def from_settings(cls, settings: Any) -> RabbitMQTopology:
        return cls(
            exchange=settings.rabbitmq_exchange,
            queue=settings.rabbitmq_queue,
            routing_key=settings.rabbitmq_routing_key,
            prefetch_count=settings.rabbitmq_prefetch_count,
        )


@dataclass(frozen=True, slots=True)
class DownloadMessage:
    job_id: uuid.UUID

    def to_bytes(self) -> bytes:
        return json.dumps(
            {"job_id": str(self.job_id)}, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")

    @classmethod
    def from_bytes(cls, body: bytes) -> DownloadMessage:
        try:
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) != {"job_id"}:
                raise ValueError
            return cls(uuid.UUID(str(payload["job_id"])))
        except (
            ValueError,
            TypeError,
            KeyError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError("invalid download message; expected only job_id") from exc


async def declare_topology(channel: Any, topology: RabbitMQTopology) -> tuple[Any, Any]:
    """Declare the one durable direct exchange/queue and bind them."""
    exchange = await channel.declare_exchange(
        topology.exchange, ExchangeType.DIRECT, durable=True
    )
    queue = await channel.declare_queue(topology.queue, durable=True)
    await queue.bind(exchange, routing_key=topology.routing_key)
    await channel.set_qos(prefetch_count=topology.prefetch_count)
    return exchange, queue


async def publish_job(
    exchange: Any, topology: RabbitMQTopology, job_id: uuid.UUID
) -> None:
    """Publish a persistent message and await aio-pika publisher confirmation."""
    await exchange.publish(
        Message(
            body=DownloadMessage(job_id).to_bytes(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        ),
        routing_key=topology.routing_key,
    )


class RabbitMQPublisher:
    """Lifecycle wrapper used by API and housekeeping publishers."""

    def __init__(self, settings: Any):
        self.settings = settings
        self.topology = RabbitMQTopology.from_settings(settings)
        self.connection: Any | None = None
        self.channel: Any | None = None
        self.exchange: Any | None = None

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
        self.channel = await self.connection.channel(publisher_confirms=True)
        self.exchange, _ = await declare_topology(self.channel, self.topology)

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.exchange = None

    async def publish(self, job_id: uuid.UUID) -> None:
        if self.exchange is None:
            raise RuntimeError("RabbitMQPublisher is not connected")
        await publish_job(self.exchange, self.topology, job_id)
