"""Run with: python -m app.workers.download.main."""

from __future__ import annotations

import asyncio
import hashlib
import os
import signal
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.download_execution import (
    DownloadExecution,
    DownloadExecutionSettings,
)
from app.core.config import Settings, get_settings_for_role
from app.core.url_cipher import URLCipher
from app.infrastructure.database import (
    SqlAlchemyDownloadRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.media_runner import MediaRunnerHttpClient, MediaRunnerRouter
from app.infrastructure.messaging import RabbitMqTopology
from app.infrastructure.object_storage import MinioObjectStorage
from app.infrastructure.url_security import FernetUrlEnvelope
from app.runner.provider_registry import configure_provider_instances
from app.workers.download.artifacts import (
    ArtifactCleanupSettings,
    ArtifactGarbageCollector,
)
from app.workers.download.consumer import RabbitMqDownloadConsumer
from app.workers.download.persistence import DownloadExecutionRepository
from app.workers.download.sweeper import (
    DownloadRecoverySweeper,
    RecoverySettings,
)
from app.workers.download.workspace import SharedWorkspaceCleaner
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class DownloadWorkerRuntime:
    consumer: RabbitMqDownloadConsumer
    sweeper: DownloadRecoverySweeper
    artifact_gc: ArtifactGarbageCollector
    storage: MinioObjectStorage
    runner: MediaRunnerRouter
    engine: AsyncEngine

    async def close(self) -> None:
        try:
            await self.consumer.close()
        finally:
            try:
                await self.runner.close()
            finally:
                await self.engine.dispose()


def build_runtime(settings: Settings) -> DownloadWorkerRuntime:
    configure_provider_instances(settings.peertube_allowed_instances)
    engine = create_engine(settings.database_url)
    raw_repository = SqlAlchemyDownloadRepository(create_session_factory(engine))
    repository = DownloadExecutionRepository(raw_repository)
    anonymous_runner = MediaRunnerHttpClient(
        base_url=settings.runner_base_url,
        secret=settings.runner_hmac_secret.get_secret_value().encode(),
        workspace_root=settings.runner_workspace_root,
        inspect_timeout_seconds=settings.inspect_timeout_seconds,
        download_timeout_seconds=settings.download_timeout_seconds,
    )
    operator_runners = {
        provider: MediaRunnerHttpClient(
            base_url=base_url,
            secret=settings.runner_hmac_secret.get_secret_value().encode(),
            workspace_root=settings.runner_workspace_root,
            inspect_timeout_seconds=settings.inspect_timeout_seconds,
            download_timeout_seconds=settings.download_timeout_seconds,
        )
        for provider, base_url in settings.runner_operator_base_urls.items()
    }
    runner = MediaRunnerRouter(anonymous_runner, operator_runners)
    storage = MinioObjectStorage(settings)
    execution = DownloadExecution(
        repository=repository,
        runner=runner,
        storage=storage,
        url_cipher=FernetUrlEnvelope(
            URLCipher(settings.url_encryption_key.get_secret_value().encode()),
            key_id=settings.url_encryption_key_id,
        ),
        workspace_cleaner=SharedWorkspaceCleaner(settings.runner_workspace_root),
        clock=_utc_now,
        settings=DownloadExecutionSettings(
            worker_id=_worker_id(),
            bucket=settings.minio_bucket,
            workspace_root=settings.runner_workspace_root,
            lease_for=timedelta(seconds=settings.job_lease_seconds),
            heartbeat_interval=settings.heartbeat_interval_seconds,
            artifact_ttl=timedelta(seconds=settings.artifact_ttl_seconds),
            max_file_size_bytes=settings.max_file_size_bytes,
        ),
    )
    topology = RabbitMqTopology(
        settings.rabbitmq_exchange,
        settings.download_queue,
        settings.download_routing_key,
    )
    return DownloadWorkerRuntime(
        consumer=RabbitMqDownloadConsumer(
            settings.rabbitmq_url,
            topology,
            execution,
            prefetch=settings.download_worker_threads,
            workers=settings.download_worker_threads,
            connection_timeout=settings.rabbitmq_connection_timeout_seconds,
            heartbeat=settings.rabbitmq_heartbeat_seconds,
            reconnect_interval=settings.rabbitmq_reconnect_interval_seconds,
        ),
        sweeper=DownloadRecoverySweeper(
            raw_repository,
            _utc_now,
            RecoverySettings(
                interval=min(5.0, settings.heartbeat_interval_seconds),
                batch_size=100,
                queued_stale_after=timedelta(
                    seconds=settings.download_queued_recovery_seconds
                ),
            ),
        ),
        artifact_gc=ArtifactGarbageCollector(
            raw_repository,
            storage.delete,
            _utc_now,
            ArtifactCleanupSettings(
                interval=settings.artifact_gc_interval_seconds,
                batch_size=settings.artifact_gc_batch_size,
                delete_timeout=settings.artifact_delete_timeout_seconds,
            ),
        ),
        storage=storage,
        runner=runner,
        engine=engine,
    )


async def run() -> None:
    runtime = build_runtime(get_settings_for_role("download-worker"))
    stop = asyncio.Event()
    _install_signal_handlers(stop)
    try:
        await _serve(runtime, stop)
    finally:
        stop.set()
        await asyncio.shield(runtime.close())


async def _serve(runtime: DownloadWorkerRuntime, stop: asyncio.Event) -> None:
    consumer = asyncio.create_task(runtime.consumer.run(stop))
    sweeper = asyncio.create_task(runtime.sweeper.run(stop))
    artifact_gc = asyncio.create_task(runtime.artifact_gc.run(stop))
    stop_wait = asyncio.create_task(stop.wait())
    tasks = (consumer, sweeper, artifact_gc)
    try:
        await asyncio.wait(
            {consumer, sweeper, artifact_gc, stop_wait},
            return_when=asyncio.FIRST_COMPLETED,
        )
        stop.set()
        await runtime.consumer.close()
        await asyncio.gather(*tasks, return_exceptions=True)
        for task in tasks:
            if task.cancelled():
                continue
            failure = task.exception()
            if failure is not None:
                raise failure
    finally:
        stop_wait.cancel()
        await asyncio.gather(stop_wait, return_exceptions=True)


def _worker_id() -> str:
    hostname = socket.gethostname()
    digest = hashlib.sha256(hostname.encode()).hexdigest()[:12]
    return f"download-{hostname[:64]}-{digest}-{os.getpid()}"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for requested_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(requested_signal, stop.set)
        except NotImplementedError:
            pass


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
