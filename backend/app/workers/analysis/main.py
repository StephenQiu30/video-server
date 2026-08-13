"""Run with: python -m app.workers.analysis.main."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote, urlsplit, urlunsplit

from app.application.analysis_execution import (
    AnalysisExecution,
    AnalysisExecutionSettings,
)
from app.core.ai_provider_cipher import FernetAiProviderSecretCipher
from app.core.config import Settings, get_settings_for_role
from app.core.url_cipher import URLCipher
from app.infrastructure.ai_provider_repository import SqlAlchemyAiProviderRepository
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.analysis_worker_registry import (
    ANALYSIS_MESSAGE_SCHEMA_VERSION,
    SqlAlchemyAnalysisWorkerRegistry,
)
from app.infrastructure.database import (
    SqlAlchemyDownloadRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.messaging import RabbitMqTopology
from app.infrastructure.object_storage import MinioObjectStorage
from app.workers.analysis.artifacts import LocalAnalysisArtifactLoader
from app.workers.analysis.consumer import RabbitMqAnalysisConsumer
from app.workers.analysis.heartbeat import AnalysisWorkerHeartbeat
from app.workers.analysis.persistence import AnalysisExecutionPersistence
from app.workers.analysis.providers import ConfiguredAnalyzerResolver
from app.workers.analysis.sweeper import (
    AnalysisRecoverySweeper,
    RecoverySettings,
)
from app.workers.analysis.utilities import install_signal_handlers, utc_now, worker_id
from sqlalchemy.ext.asyncio import AsyncEngine

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalysisWorkerRuntime:
    consumer: RabbitMqAnalysisConsumer
    sweeper: AnalysisRecoverySweeper
    heartbeat: AnalysisWorkerHeartbeat
    storage: MinioObjectStorage
    loader: LocalAnalysisArtifactLoader
    engine: AsyncEngine
    resolver: ConfiguredAnalyzerResolver

    async def close(self) -> None:
        try:
            await self.consumer.close()
        finally:
            try:
                await self.heartbeat.close()
            finally:
                await self.engine.dispose()


def build_runtime(settings: Settings) -> AnalysisWorkerRuntime:
    minio_access_key, minio_secret_key = settings.analysis_minio_credentials()
    host_settings = settings.model_copy(
        update={
            "database_url": settings.analysis_database_url,
            "rabbitmq_url": _rabbitmq_worker_url(
                settings.analysis_rabbitmq_url, settings.rabbitmq_vhost
            ),
            "minio_endpoint": settings.analysis_minio_endpoint,
            "minio_access_key": minio_access_key,
            "minio_secret_key": minio_secret_key,
        }
    )
    engine = create_engine(host_settings.database_url)
    sessions = create_session_factory(engine)
    resolver = ConfiguredAnalyzerResolver(
        settings,
        SqlAlchemyAiProviderRepository(sessions),
        FernetAiProviderSecretCipher(
            URLCipher(settings.url_encryption_key.get_secret_value().encode()),
            key_id=settings.url_encryption_key_id,
        ),
    )
    analysis = SqlAlchemyAnalysisRepository(sessions)
    runtime_worker_id = worker_id()
    worker_registry = SqlAlchemyAnalysisWorkerRegistry(
        sessions,
        expected_app_version=settings.app_version,
        expected_message_schema_version=ANALYSIS_MESSAGE_SCHEMA_VERSION,
        stale_after=timedelta(seconds=settings.analysis_worker_stale_seconds),
    )
    persistence = AnalysisExecutionPersistence(
        analysis, SqlAlchemyDownloadRepository(sessions)
    )
    storage = MinioObjectStorage(host_settings)
    loader = LocalAnalysisArtifactLoader(
        storage,
        workspace_root=settings.analysis_workspace_root,
        bucket=settings.minio_bucket,
        max_source_bytes=settings.max_file_size_bytes,
    )
    execution = AnalysisExecution(
        repository=persistence,
        loader=loader,
        resolver=resolver,
        clock=utc_now,
        settings=AnalysisExecutionSettings(
            worker_id=runtime_worker_id,
            bucket=settings.minio_bucket,
            lease_for=timedelta(seconds=settings.job_lease_seconds),
            heartbeat_interval=settings.heartbeat_interval_seconds,
            max_source_bytes=settings.max_file_size_bytes,
        ),
    )
    topology = RabbitMqTopology(
        settings.rabbitmq_exchange,
        settings.download_queue,
        settings.download_routing_key,
        settings.analysis_queue,
        settings.analysis_routing_key,
        settings.analysis_report_queue,
        settings.analysis_report_routing_key,
    )
    return AnalysisWorkerRuntime(
        consumer=RabbitMqAnalysisConsumer(
            host_settings.rabbitmq_url,
            topology,
            execution,
            prefetch=1,
            connection_timeout=settings.rabbitmq_connection_timeout_seconds,
            heartbeat=settings.rabbitmq_heartbeat_seconds,
            reconnect_interval=settings.rabbitmq_reconnect_interval_seconds,
        ),
        sweeper=AnalysisRecoverySweeper(
            analysis,
            utc_now,
            RecoverySettings(
                interval=min(5.0, settings.heartbeat_interval_seconds),
                batch_size=100,
                queued_stale_after=timedelta(
                    seconds=settings.analysis_queued_recovery_seconds
                ),
            ),
        ),
        heartbeat=AnalysisWorkerHeartbeat(
            worker_registry,
            worker_id=runtime_worker_id,
            app_version=settings.app_version,
            message_schema_version=ANALYSIS_MESSAGE_SCHEMA_VERSION,
            interval=settings.analysis_worker_heartbeat_seconds,
            clock=utc_now,
        ),
        storage=storage,
        loader=loader,
        engine=engine,
        resolver=resolver,
    )


async def run() -> None:
    runtime = build_runtime(get_settings_for_role("analysis-worker"))
    stop = asyncio.Event()
    install_signal_handlers(stop)
    try:
        await runtime.loader.prepare_root()
        await runtime.resolver.resolve()
        await _serve(runtime, stop)
    finally:
        stop.set()
        await asyncio.shield(runtime.close())


async def _serve(runtime: AnalysisWorkerRuntime, stop: asyncio.Event) -> None:
    tasks = (
        asyncio.create_task(
            _run_resilient("consumer", runtime.consumer.run, stop),
            name="analysis-consumer",
        ),
        asyncio.create_task(
            _run_resilient("sweeper", runtime.sweeper.run, stop),
            name="analysis-sweeper",
        ),
        asyncio.create_task(
            _run_resilient("heartbeat", runtime.heartbeat.run, stop),
            name="analysis-heartbeat",
        ),
    )
    try:
        await stop.wait()
    finally:
        stop.set()
        await runtime.consumer.close()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _run_resilient(
    component: str,
    operation: object,
    stop: asyncio.Event,
) -> None:
    delay = 1.0
    while not stop.is_set():
        try:
            await operation(stop)  # type: ignore[operator]
            if stop.is_set():
                return
        except asyncio.CancelledError:
            raise
        except Exception:
            _log.exception("analysis worker %s failed; restarting", component)
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except TimeoutError:
            delay = min(delay * 2, 30.0)


def main() -> None:
    asyncio.run(run())


def _rabbitmq_worker_url(url: str, vhost: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit(parsed._replace(path=f"/{quote(vhost, safe='')}"))


if __name__ == "__main__":
    main()
