"""Opt-in delivery test against an existing broker; only isolated names are removed."""

import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import aio_pika
import pytest
from app.integrations.messaging import RabbitMqTopology
from app.integrations.messaging.rabbitmq import RabbitMqPublisher
from app.models import MediaInspectionRow, OutboxEventRow
from app.repositories.outbox_repository import SqlAlchemyOutboxRepository
from app.workers.download.consumer import (
    RabbitMqDownloadConsumer,
    _declare_download_topology,
)
from app.workers.outbox.loop import OutboxPublisherLoop
from sqlalchemy import func, select
from tests.integration.api.test_download_intent_routes import URL, components
from tests.integration.api.test_download_routes import TEST_USER


async def test_deployed_download_role_can_declare_both_command_queues():
    url = os.environ.get("TEST_RABBITMQ_DOWNLOAD_URL")
    if not url:
        pytest.skip("existing deployment download-role URL not supplied")
    # Re-declare the existing bounded topology only. Do not consume or remove
    # deployment queues; this catches ACL drift hidden by administrator tests.
    topology = RabbitMqTopology("video.events", "video.download", "download.requested")
    connection = await aio_pika.connect_robust(url, timeout=5)
    try:
        channel = await connection.channel()
        async with asyncio.timeout(10):
            await _declare_download_topology(channel, topology)
            await _declare_download_topology(channel, topology, intent=True)
    finally:
        await connection.close()


async def test_intent_outbox_delivery_and_duplicate_after_confirm_loss(postgres_engine):
    url = os.environ.get("TEST_RABBITMQ_URL")
    if not url:
        pytest.skip("TEST_RABBITMQ_URL must point to an existing test broker")
    name = f"test.intent.{uuid4().hex}"
    topology = RabbitMqTopology(
        exchange=name,
        download_queue=f"{name}.unused",
        download_routing_key="download.requested",
        intent_queue=f"{name}.intent",
    )
    service, _, executor, clock, sessions = components(postgres_engine)
    deliveries = []

    class Handler:
        async def execute(self, intent_id):
            result = await executor.execute(intent_id)
            deliveries.append(intent_id)
            return result

    consumer = RabbitMqDownloadConsumer(
        url, topology, Handler(), prefetch=2, intent=True
    )
    publisher = RabbitMqPublisher(url, topology)
    repository = SqlAlchemyOutboxRepository(sessions)
    loop = OutboxPublisherLoop(
        repository=repository,
        publisher=publisher,
        publisher_id="test-publisher",
        clock=lambda: clock[0],
        random_value=lambda: 0.5,
    )
    intent = await service.create(URL, TEST_USER.owner_hash, "outbox")
    # No broker connection: acceptance remains durable and publishing is retriable.
    assert await loop.run_once() == 1
    async with sessions() as session:
        event = await session.scalar(select(OutboxEventRow))
        assert event.published_at is None and event.publish_attempts == 1
    try:
        await consumer.start()
        await publisher.start()
        clock[0] += timedelta(seconds=2)
        assert await loop.run_once() == 1
        async with asyncio.timeout(10):
            while (
                await service.get(intent.id, TEST_USER.owner_hash)
            ).status != "ready":
                await asyncio.sleep(0.02)
        # Model publisher crash after broker confirmation, before database ACK.
        async with sessions() as session, session.begin():
            event = await session.scalar(select(OutboxEventRow).with_for_update())
            assert event.published_at is not None
            event.published_at = None
        assert await loop.run_once() == 1
        async with asyncio.timeout(10):
            while len(deliveries) < 2:
                await asyncio.sleep(0.02)
        assert deliveries == [intent.id, intent.id]
        await consumer.close()  # Drain real deliveries before inspecting persistence.
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count()).select_from(MediaInspectionRow)
                )
                == 1
            )
            event = await session.scalar(select(OutboxEventRow))
            assert event.published_at is not None and event.publish_attempts == 3
    finally:
        await consumer.close()
        await publisher.close()
        connection = await aio_pika.connect(url)
        async with connection:
            channel = await connection.channel()
            await channel.queue_delete(
                topology.intents.queue, if_unused=False, if_empty=False
            )
            await channel.queue_delete(
                topology.intents.dead_queue, if_unused=False, if_empty=False
            )
            await channel.exchange_delete(topology.exchange)
            await channel.exchange_delete(topology.dead_exchange)
