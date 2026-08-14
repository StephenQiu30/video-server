"""Run with: python -m app.workers.imports.main."""

from __future__ import annotations

import asyncio
import hashlib
import os
import signal
import socket
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.import_execution import (
    ImportExecution,
    ImportExecutionSettings,
    ImportRecoverySweeper,
)
from app.core.config import Settings, get_settings_for_role
from app.infrastructure.database import (
    SqlAlchemyMediaImportRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.messaging import RabbitMqTopology
from app.infrastructure.object_storage import MinioObjectStorage
from app.workers.imports.consumer import RabbitMqImportConsumer
from app.workers.imports.video import (
    Mp4ImportVerifier,
    VideoVerificationSettings,
)
from app.workers.imports.workspace import PrivateImportWorkspace
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class ImportWorkerRuntime:
    consumer: RabbitMqImportConsumer
    sweeper: ImportRecoverySweeper
    engine: AsyncEngine

    async def close(self) -> None:
        try:
            await self.consumer.close()
        finally:
            await self.engine.dispose()


def build_runtime(settings: Settings) -> ImportWorkerRuntime:
    engine = create_engine(settings.database_url)
    repository = SqlAlchemyMediaImportRepository(create_session_factory(engine))
    storage = MinioObjectStorage.for_imports(settings, enable_public_signing=False)
    workspace = PrivateImportWorkspace(settings.import_workspace_root)
    execution = ImportExecution(
        repository=repository,
        storage=storage,
        workspace=workspace,
        video_verifier=Mp4ImportVerifier(
            settings.import_workspace_root,
            VideoVerificationSettings(
                ffprobe_binary=settings.import_ffprobe_binary,
                ffprobe_timeout_seconds=settings.import_ffprobe_timeout_seconds,
                max_probe_output_bytes=settings.import_max_probe_output_bytes,
                max_size_bytes=settings.media_import_max_bytes,
                max_duration_seconds=settings.max_video_duration_seconds,
                max_width=settings.import_max_video_width,
                max_height=settings.import_max_video_height,
                max_streams=settings.import_max_media_streams,
            ),
        ),
        clock=_utc_now,
        settings=ImportExecutionSettings(
            worker_id=_worker_id(),
            bucket=settings.minio_bucket,
            workspace_root=settings.import_workspace_root,
            lease_for=timedelta(seconds=settings.job_lease_seconds),
            heartbeat_interval=settings.heartbeat_interval_seconds,
            artifact_ttl=timedelta(seconds=settings.artifact_ttl_seconds),
        ),
    )
    topology = RabbitMqTopology(
        exchange=settings.rabbitmq_exchange,
        download_queue=settings.download_queue,
        download_routing_key=settings.download_routing_key,
        analysis_queue=settings.analysis_queue,
        analysis_routing_key=settings.analysis_routing_key,
        report_queue=settings.analysis_report_queue,
        report_routing_key=settings.analysis_report_routing_key,
        import_queue=settings.import_queue,
        import_routing_key=settings.import_routing_key,
    )
    return ImportWorkerRuntime(
        consumer=RabbitMqImportConsumer(
            settings.rabbitmq_url,
            topology,
            execution,
            prefetch=settings.worker_prefetch,
            connection_timeout=settings.rabbitmq_connection_timeout_seconds,
            heartbeat=settings.rabbitmq_heartbeat_seconds,
            reconnect_interval=settings.rabbitmq_reconnect_interval_seconds,
        ),
        sweeper=ImportRecoverySweeper(
            repository,
            storage,
            workspace,
            _utc_now,
            interval=settings.import_recovery_interval_seconds,
            batch_size=settings.import_recovery_batch_size,
            workspace_grace=timedelta(seconds=settings.import_workspace_grace_seconds),
            artifact_orphan_grace=timedelta(
                seconds=settings.import_artifact_orphan_grace_seconds
            ),
            delete_timeout=settings.artifact_delete_timeout_seconds,
        ),
        engine=engine,
    )


async def run() -> None:
    runtime = build_runtime(get_settings_for_role("import-worker"))
    stop = asyncio.Event()
    _install_signal_handlers(stop)
    try:
        await _serve(runtime, stop)
    finally:
        stop.set()
        await asyncio.shield(runtime.close())


async def _serve(runtime: ImportWorkerRuntime, stop: asyncio.Event) -> None:
    consumer = asyncio.create_task(runtime.consumer.run(stop))
    sweeper = asyncio.create_task(runtime.sweeper.run(stop))
    stop_wait = asyncio.create_task(stop.wait())
    tasks = (consumer, sweeper)
    try:
        await asyncio.wait(
            {consumer, sweeper, stop_wait}, return_when=asyncio.FIRST_COMPLETED
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
    return f"import-{hostname[:64]}-{digest}-{os.getpid()}"


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
