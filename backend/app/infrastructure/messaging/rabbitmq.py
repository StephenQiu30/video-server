"""aio-pika robust publisher with mandatory broker confirmations."""

from __future__ import annotations

import asyncio

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import AbstractExchange, AbstractRobustConnection
from pamqp.commands import Basic

from .envelope import EventEnvelope
from .topology import RabbitMqTopology


class PublishNotConfirmed(RuntimeError):
    """RabbitMQ did not positively acknowledge a mandatory publish."""


class RabbitMqPublisher:
    def __init__(
        self,
        url: str,
        topology: RabbitMqTopology,
        *,
        connection_timeout: float = 10,
        publish_timeout: float = 10,
    ) -> None:
        if not url:
            raise ValueError("RabbitMQ URL cannot be blank")
        if connection_timeout <= 0 or publish_timeout <= 0:
            raise ValueError("RabbitMQ timeouts must be positive")
        self._url = url
        self._topology = topology
        self._connection_timeout = connection_timeout
        self._publish_timeout = publish_timeout
        self._connection: AbstractRobustConnection | None = None
        self._exchange: AbstractExchange | None = None

    async def start(self) -> None:
        if self._connection is not None:
            return
        connection = await aio_pika.connect_robust(
            self._url,
            timeout=self._connection_timeout,
            client_properties={"connection_name": "video-server-outbox"},
        )
        self._connection = connection
        try:
            async with asyncio.timeout(self._connection_timeout):
                channel = await connection.channel(
                    publisher_confirms=True,
                    on_return_raises=True,
                )
                exchange = await channel.declare_exchange(
                    self._topology.exchange,
                    ExchangeType.TOPIC,
                    durable=True,
                )
                dead_exchange = await channel.declare_exchange(
                    self._topology.dead_exchange,
                    ExchangeType.DIRECT,
                    durable=True,
                )
                dead_queue = await channel.declare_queue(
                    self._topology.dead_queue,
                    durable=True,
                )
                await dead_queue.bind(
                    dead_exchange,
                    routing_key=self._topology.dead_routing_key,
                )
                queue = await channel.declare_queue(
                    self._topology.download_queue,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": self._topology.dead_exchange,
                        "x-dead-letter-routing-key": self._topology.dead_routing_key,
                        "x-message-ttl": self._topology.message_ttl_ms,
                    },
                )
                await queue.bind(
                    exchange,
                    routing_key=self._topology.download_routing_key,
                )
            self._exchange = exchange
        except BaseException:
            await asyncio.shield(self.close())
            raise

    async def publish(self, envelope: EventEnvelope) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQ publisher has not been started")
        message = Message(
            envelope.to_bytes(),
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=str(envelope.aggregate_id),
            message_id=str(envelope.event_id),
            timestamp=envelope.occurred_at,
            type=envelope.event_type,
            app_id="video-server-outbox",
            headers={"schema_version": envelope.schema_version},
        )
        confirmation = await self._exchange.publish(
            message,
            routing_key=envelope.event_type,
            mandatory=True,
            timeout=self._publish_timeout,
        )
        if not isinstance(confirmation, Basic.Ack):
            raise PublishNotConfirmed("broker did not ack mandatory publish")

    async def close(self) -> None:
        connection = self._connection
        self._connection = None
        self._exchange = None
        if connection is not None:
            await connection.close()
