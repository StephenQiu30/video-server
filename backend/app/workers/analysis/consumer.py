from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Protocol
from uuid import UUID

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from app.application.analysis_execution import AnalysisDisposition
from app.infrastructure.messaging import RabbitMqTopology

from .message import AnalysisMessageError, parse_analysis_requested


class AnalysisHandler(Protocol):
    async def execute(
        self, job_id: UUID, run_id: UUID, run_no: int, expected_version: int
    ) -> AnalysisDisposition: ...


class Delivery(Protocol):
    body: bytes
    redelivered: bool | None

    async def ack(self) -> None: ...

    async def nack(self, *, requeue: bool) -> None: ...


async def process_delivery(message: Delivery, handler: AnalysisHandler) -> None:
    try:
        requested = parse_analysis_requested(message.body)
    except AnalysisMessageError:
        await message.nack(requeue=False)
        return
    try:
        disposition = await handler.execute(
            requested.job_id,
            requested.run_id,
            requested.run_no,
            requested.version,
        )
    except asyncio.CancelledError:
        with suppress(Exception):
            await asyncio.shield(message.nack(requeue=True))
        raise
    except Exception:
        await message.nack(requeue=not bool(message.redelivered))
        return
    if disposition is AnalysisDisposition.ACK:
        await message.ack()
    else:
        await message.nack(requeue=not bool(message.redelivered))


class RabbitMqAnalysisConsumer:
    def __init__(
        self,
        url: str,
        topology: RabbitMqTopology,
        handler: AnalysisHandler,
        *,
        prefetch: int,
        connection_timeout: float = 10,
    ) -> None:
        if not url or prefetch < 1 or connection_timeout <= 0:
            raise ValueError("invalid RabbitMQ consumer settings")
        self._url = url
        self._topology = topology
        self._handler = handler
        self._prefetch = prefetch
        self._connection_timeout = connection_timeout
        self._connection: AbstractRobustConnection | None = None
        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None
        self._active: set[asyncio.Task[object]] = set()

    async def start(self) -> None:
        if self._connection is not None:
            return
        connection = await aio_pika.connect_robust(
            self._url,
            timeout=self._connection_timeout,
            client_properties={"connection_name": "video-server-analysis-worker"},
        )
        self._connection = connection
        try:
            async with asyncio.timeout(self._connection_timeout):
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=self._prefetch)
                exchange = await channel.declare_exchange(
                    self._topology.exchange, ExchangeType.TOPIC, durable=True
                )
                dead_exchange = await channel.declare_exchange(
                    self._topology.dead_exchange, ExchangeType.DIRECT, durable=True
                )
                binding = self._topology.analysis
                dead_queue = await channel.declare_queue(
                    binding.dead_queue, durable=True
                )
                await dead_queue.bind(
                    dead_exchange, routing_key=binding.dead_routing_key
                )
                queue = await channel.declare_queue(
                    binding.queue,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": self._topology.dead_exchange,
                        "x-dead-letter-routing-key": binding.dead_routing_key,
                        "x-message-ttl": binding.message_ttl_ms,
                        "x-max-length": binding.max_length,
                        "x-overflow": "reject-publish-dlx",
                    },
                )
                await queue.bind(exchange, routing_key=binding.routing_key)
                self._queue = queue
                self._consumer_tag = await queue.consume(self._consume)
        except BaseException:
            await asyncio.shield(self.close())
            raise

    async def run(self, stop: asyncio.Event) -> None:
        await self.start()
        await stop.wait()

    async def close(self) -> None:
        queue, tag = self._queue, self._consumer_tag
        self._queue = None
        self._consumer_tag = None
        if queue is not None and tag is not None:
            with suppress(Exception):
                await queue.cancel(tag)
        active = tuple(self._active)
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()

    async def _consume(self, message: AbstractIncomingMessage) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._active.add(task)
        try:
            await process_delivery(message, self._handler)
        finally:
            if task is not None:
                self._active.discard(task)
