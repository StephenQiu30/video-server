"""Run with: python -m app.workers.analysis.main."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from app.application.analysis_execution import (
    AnalysisExecution,
    AnalysisExecutionSettings,
)
from app.core.config import Settings, get_settings
from app.infrastructure.ai import (
    LangChainAnalyzer,
    OpenAITranscriber,
    create_transcription_client,
)
from app.infrastructure.analysis_media import (
    AnalysisMediaSettings,
    FfmpegAudioPreprocessor,
)
from app.infrastructure.analysis_repository import SqlAlchemyAnalysisRepository
from app.infrastructure.database import (
    SqlAlchemyDownloadRepository,
    create_engine,
    create_session_factory,
)
from app.infrastructure.object_storage import MinioObjectStorage
from app.workers.analysis.artifacts import LocalAnalysisArtifactLoader
from app.workers.analysis.consumer import (
    AnalysisQueueTopology,
    RabbitMqAnalysisConsumer,
)
from app.workers.analysis.persistence import AnalysisExecutionPersistence
from app.workers.analysis.providers import (
    analysis_model_config,
    transcription_config,
)
from app.workers.analysis.sweeper import (
    AnalysisRecoverySweeper,
    RecoverySettings,
)
from app.workers.analysis.utilities import install_signal_handlers, utc_now, worker_id
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(slots=True)
class AnalysisWorkerRuntime:
    consumer: RabbitMqAnalysisConsumer
    sweeper: AnalysisRecoverySweeper
    storage: MinioObjectStorage
    loader: LocalAnalysisArtifactLoader
    transcription_client: AsyncOpenAI
    engine: AsyncEngine

    async def close(self) -> None:
        try:
            await self.consumer.close()
        finally:
            try:
                await self.transcription_client.close()
            finally:
                await self.engine.dispose()


def build_runtime(settings: Settings) -> AnalysisWorkerRuntime:
    transcription = transcription_config(settings)
    transcription_client = create_transcription_client(transcription)
    analysis_model = analysis_model_config(settings)
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    analysis = SqlAlchemyAnalysisRepository(sessions)
    persistence = AnalysisExecutionPersistence(
        analysis, SqlAlchemyDownloadRepository(sessions)
    )
    storage = MinioObjectStorage(settings)
    loader = LocalAnalysisArtifactLoader(
        storage,
        workspace_root=settings.analysis_workspace_root,
        bucket=settings.minio_bucket,
        max_source_bytes=settings.max_file_size_bytes,
    )
    execution = AnalysisExecution(
        repository=persistence,
        loader=loader,
        preprocessor=FfmpegAudioPreprocessor(
            AnalysisMediaSettings(
                max_total_duration_ms=settings.max_video_duration_seconds * 1000
            )
        ),
        transcriber=OpenAITranscriber(
            transcription,
            client=transcription_client,
        ),
        analyzer=LangChainAnalyzer(analysis_model),
        clock=utc_now,
        settings=AnalysisExecutionSettings(
            worker_id=worker_id(),
            bucket=settings.minio_bucket,
            lease_for=timedelta(seconds=settings.job_lease_seconds),
            heartbeat_interval=settings.heartbeat_interval_seconds,
            max_source_bytes=settings.max_file_size_bytes,
        ),
    )
    topology = AnalysisQueueTopology(
        settings.rabbitmq_exchange,
        settings.analysis_queue,
        settings.analysis_routing_key,
    )
    return AnalysisWorkerRuntime(
        consumer=RabbitMqAnalysisConsumer(
            settings.rabbitmq_url,
            topology,
            execution,
            prefetch=settings.worker_prefetch,
        ),
        sweeper=AnalysisRecoverySweeper(
            analysis,
            utc_now,
            RecoverySettings(
                interval=min(5.0, settings.heartbeat_interval_seconds),
                batch_size=100,
            ),
        ),
        storage=storage,
        loader=loader,
        transcription_client=transcription_client,
        engine=engine,
    )


async def run() -> None:
    runtime = build_runtime(get_settings())
    stop = asyncio.Event()
    install_signal_handlers(stop)
    try:
        await runtime.storage.ensure_bucket()
        await runtime.loader.prepare_root()
        await _serve(runtime, stop)
    finally:
        stop.set()
        await asyncio.shield(runtime.close())


async def _serve(runtime: AnalysisWorkerRuntime, stop: asyncio.Event) -> None:
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


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
