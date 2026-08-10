from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Protocol
from uuid import UUID

import aio_pika
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from app.application.download_execution import ExecutionDisposition
from app.infrastructure.messaging import RabbitMqTopology

from .message import DownloadMessageError, parse_download_requested
from .pool import AsyncWorkerPool


class DownloadHandler(Protocol):
    async def execute(self, job_id: UUID) -> ExecutionDisposition: ...


class Delivery(Protocol):
    body: bytes

    async def ack(self) -> None: ...

    async def nack(self, *, requeue: bool) -> None: ...


async def process_delivery(message: Delivery, handler: DownloadHandler) -> None:
    try:
        requested = parse_download_requested(message.body)
    except DownloadMessageError:
        await message.nack(requeue=False)
        return
    try:
        result = await handler.execute(requested.job_id)
    except asyncio.CancelledError:
        with suppress(Exception):
            await asyncio.shield(message.nack(requeue=True))
        raise
    except Exception:
        await message.nack(requeue=True)
        return
    if result is ExecutionDisposition.ACK:
        await message.ack()
    else:
        await message.nack(requeue=True)


class RabbitMqDownloadConsumer:
    def __init__(
        self,
        url: str,
        topology: RabbitMqTopology,
        handler: DownloadHandler,
        *,
        prefetch: int,
        workers: int | None = None,
        connection_timeout: float = 10,
    ) -> None:
        worker_count = prefetch if workers is None else workers
        if not url or prefetch < 1 or worker_count < 1 or connection_timeout <= 0:
            raise ValueError("invalid RabbitMQ consumer settings")
        self._url = url
        self._topology = topology
        self._handler = handler
        self._prefetch = prefetch
        self._pool = AsyncWorkerPool(
            self._consume_delivery,
            workers=worker_count,
        )
        self._connection_timeout = connection_timeout
        self._connection: AbstractRobustConnection | None = None
        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None

    async def start(self) -> None:
        if self._connection is not None:
            return
        connection = await aio_pika.connect_robust(
            self._url,
            timeout=self._connection_timeout,
            client_properties={"connection_name": "video-server-download-worker"},
        )
        self._connection = connection
        try:
            async with asyncio.timeout(self._connection_timeout):
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=self._prefetch)
                queue = await channel.declare_queue(
                    self._topology.download_queue, passive=True
                )
                self._queue = queue
                await self._pool.start()
                self._consumer_tag = await queue.consume(self._consume)
        except BaseException:
            await asyncio.shield(self.close())
            raise

    async def run(self, stop: asyncio.Event) -> None:
        await self.start()
        await stop.wait()

    async def close(self) -> None:
        queue, consumer_tag = self._queue, self._consumer_tag
        self._queue = None
        self._consumer_tag = None
        if queue is not None and consumer_tag is not None:
            with suppress(Exception):
                await queue.cancel(consumer_tag)
        await self._pool.close()
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()

    async def _consume(self, message: AbstractIncomingMessage) -> None:
        await self._pool.submit(message)

    async def _consume_delivery(self, message: AbstractIncomingMessage) -> None:
        await process_delivery(message, self._handler)
