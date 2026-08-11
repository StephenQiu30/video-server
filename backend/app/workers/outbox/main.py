"""Run with: python -m app.workers.outbox.main."""

from __future__ import annotations

import asyncio
import hashlib
import os
import signal
import socket
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings_for_role
from app.infrastructure.database import (
    SqlAlchemyDownloadRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.messaging import RabbitMqPublisher, RabbitMqTopology
from app.workers.outbox.loop import OutboxLoopSettings, OutboxPublisherLoop


def _publisher_id() -> str:
    hostname = socket.gethostname()
    digest = hashlib.sha256(hostname.encode()).hexdigest()[:12]
    return f"outbox-{hostname[:80]}-{digest}-{os.getpid()}"


async def run() -> None:
    settings = get_settings_for_role("outbox")
    engine = create_engine(settings.database_url)
    repository = SqlAlchemyDownloadRepository(create_session_factory(engine))
    publisher = RabbitMqPublisher(
        settings.rabbitmq_url,
        RabbitMqTopology(
            settings.rabbitmq_exchange,
            settings.download_queue,
            settings.download_routing_key,
            settings.analysis_queue,
            settings.analysis_routing_key,
            settings.analysis_report_queue,
            settings.analysis_report_routing_key,
        ),
        connection_timeout=settings.rabbitmq_connection_timeout_seconds,
        publish_timeout=settings.rabbitmq_publish_timeout_seconds,
        heartbeat=settings.rabbitmq_heartbeat_seconds,
        reconnect_interval=settings.rabbitmq_reconnect_interval_seconds,
    )
    publisher_loop = OutboxPublisherLoop(
        repository=repository,
        publisher=publisher,
        publisher_id=_publisher_id(),
        clock=lambda: datetime.now(UTC),
        settings=OutboxLoopSettings(
            batch_size=settings.outbox_batch_size,
            claim_lease=timedelta(seconds=settings.job_lease_seconds),
            poll_interval=settings.outbox_poll_interval_seconds,
        ),
    )
    stop = asyncio.Event()
    event_loop = asyncio.get_running_loop()
    try:
        for requested_signal in (signal.SIGINT, signal.SIGTERM):
            try:
                event_loop.add_signal_handler(requested_signal, stop.set)
            except NotImplementedError:
                pass
        await publisher.start()
        await publisher_loop.run(stop)
    finally:
        try:
            await publisher.close()
        finally:
            await engine.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
