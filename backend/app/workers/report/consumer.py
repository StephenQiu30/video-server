"""RabbitMQ consumer for isolated report publication work."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import aio_pika
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from app.infrastructure.messaging import RabbitMqTopology

from .message import ReportMessageError, parse_report_requested
from .publisher import ReportPublisher


async def process_delivery(
    message: AbstractIncomingMessage, publisher: ReportPublisher
) -> None:
    try:
        requested = parse_report_requested(message.body)
    except ReportMessageError:
        await message.nack(requeue=False)
        return
    try:
        complete = await publisher.execute(requested)
    except asyncio.CancelledError:
        with suppress(Exception):
            await asyncio.shield(message.nack(requeue=True))
        raise
    except Exception:
        complete = False
    if complete:
        await message.ack()
    else:
        await message.nack(requeue=not bool(message.redelivered))


class RabbitMqReportConsumer:
    def __init__(
        self,
        url: str,
        topology: RabbitMqTopology,
        publisher: ReportPublisher,
        *,
        connection_timeout: float = 10,
    ) -> None:
        self._url = url
        self._topology = topology
        self._publisher = publisher
        self._connection_timeout = connection_timeout
        self._connection: AbstractRobustConnection | None = None
        self._queue: AbstractQueue | None = None
        self._tag: str | None = None

    async def start(self) -> None:
        connection = await aio_pika.connect_robust(
            self._url,
            timeout=self._connection_timeout,
            client_properties={"connection_name": "video-server-report-worker"},
        )
        self._connection = connection
        try:
            async with asyncio.timeout(self._connection_timeout):
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=2)
                binding = self._topology.report
                queue = await channel.declare_queue(binding.queue, passive=True)
                self._queue = queue
                self._tag = await queue.consume(self._consume)
        except BaseException:
            await asyncio.shield(self.close())
            raise

    async def run(self, stop: asyncio.Event) -> None:
        await self.start()
        await stop.wait()

    async def close(self) -> None:
        if self._queue is not None and self._tag is not None:
            with suppress(Exception):
                await self._queue.cancel(self._tag)
        self._queue = None
        self._tag = None
        if self._connection is not None:
            await self._connection.close()
        self._connection = None

    async def _consume(self, message: AbstractIncomingMessage) -> None:
        await process_delivery(message, self._publisher)
