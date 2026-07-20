"""Download Worker message handling and the single lightweight housekeeping loop."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

import aio_pika

from src.downloads.repository import DownloadRepository
from src.downloads.state import JobStatus
from src.media.download import DownloadLimits, MediaDownloader, job_workspace
from src.media.formats import NormalizedFormat
from src.minio_client import MinioStorage
from src.rabbitmq import (
    DownloadMessage,
    RabbitMQPublisher,
    RabbitMQTopology,
    declare_topology,
)


class WorkerSession(Protocol):
    async def __aenter__(self) -> Any: ...

    async def __aexit__(self, *args: object) -> None: ...


class SessionFactory(Protocol):
    def __call__(self, **kwargs: Any) -> WorkerSession: ...


class DownloadProcessor(Protocol):
    async def __call__(self, job_id: uuid.UUID) -> ArtifactPayload: ...


@dataclass(frozen=True, slots=True)
class ArtifactPayload:
    object_key: str
    file_name: str
    content_type: str
    size_bytes: int
    sha256: str
    expires_at: Any


class DefaultDownloadProcessor:
    """Run the constrained media pipeline and upload one private artifact."""

    def __init__(self, settings: Any, session_factory: SessionFactory) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.storage = MinioStorage(settings)
        self.downloader = MediaDownloader(
            limits=DownloadLimits(
                timeout_seconds=settings.download_timeout_seconds,
                max_size_bytes=settings.max_file_size_bytes,
                max_duration_seconds=settings.max_video_duration_seconds,
                temp_dir=settings.worker_temp_dir,
            )
        )

    async def __call__(self, job_id: uuid.UUID) -> ArtifactPayload:
        async with self.session_factory() as session:
            repository = DownloadRepository(session)
            job = await repository.get_worker_job(job_id, lock=False)
            if job is None or job.source is None or job.format is None:
                raise RuntimeError("download job data is unavailable")
            if not job.source.source_url:
                raise RuntimeError("download source URL has expired")
            option = NormalizedFormat(
                video_format_id=job.format.video_format_id,
                audio_format_id=job.format.audio_format_id,
                label=job.format.label,
                width=job.format.width,
                height=job.format.height,
                fps=float(job.format.fps) if job.format.fps is not None else None,
                container=job.format.container,
                video_codec=job.format.video_codec,
                audio_codec=job.format.audio_codec,
                estimated_size_bytes=job.format.estimated_size_bytes,
                requires_merge=job.format.requires_merge,
                sort_order=job.format.sort_order,
            )
            source_url = job.source.source_url
            title = job.source.title

        with job_workspace(job_id, root=self.settings.worker_temp_dir) as workspace:
            media = await asyncio.to_thread(
                self.downloader.download_to_workspace,
                source_url=source_url,
                format_option=option,
                title=title,
                workspace=workspace,
            )
            object_key = (
                f"jobs/{job_id}/{uuid.uuid4()}{media.path.suffix.lower() or '.mp4'}"
            )
            await self.storage.put_file(
                object_key,
                media.path,
                content_type=media.content_type,
                size_bytes=media.size_bytes,
            )

        return ArtifactPayload(
            object_key=object_key,
            file_name=media.file_name,
            content_type=media.content_type,
            size_bytes=media.size_bytes,
            sha256=media.sha256,
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.settings.artifact_ttl_seconds),
        )


@dataclass(slots=True)
class WorkerConsumer:
    session_factory: SessionFactory
    processor: DownloadProcessor

    async def handle_message(self, message: Any) -> None:
        """Handle one delivery with manual ack and database-led idempotency."""
        try:
            payload = DownloadMessage.from_bytes(message.body)
        except ValueError:
            await message.reject(requeue=False)
            return

        job_id = payload.job_id
        try:
            async with self.session_factory() as session:
                repository = DownloadRepository(session)
                job = await repository.get_worker_job(job_id, lock=True)
                if job is None or job.status in {
                    status.value
                    for status in (
                        JobStatus.SUCCEEDED,
                        JobStatus.FAILED,
                        JobStatus.EXPIRED,
                    )
                }:
                    await session.commit()
                    await message.ack()
                    return
                # A duplicate delivery for a job already claimed by a live
                # worker must not execute concurrently or create a second file.
                if job.status == JobStatus.RUNNING.value:
                    await session.commit()
                    await message.ack()
                    return
                await repository.transition(
                    job_id, expected=JobStatus.QUEUED, target=JobStatus.RUNNING
                )
                await session.commit()

            try:
                artifact = await self.processor(job_id)
            except Exception as exc:
                async with self.session_factory() as failure_session:
                    failure_repository = DownloadRepository(failure_session)
                    try:
                        await failure_repository.transition(
                            job_id,
                            expected=JobStatus.RUNNING,
                            target=JobStatus.FAILED,
                            error_code="worker_failed",
                            error_message=str(exc)[:500],
                        )
                    except Exception:
                        await failure_session.rollback()
                        raise
                    await failure_session.commit()
                await message.ack()
                return

            async with self.session_factory() as success_session:
                success_repository = DownloadRepository(success_session)
                await success_repository.succeed_with_artifact(
                    job_id,
                    object_key=artifact.object_key,
                    file_name=artifact.file_name,
                    content_type=artifact.content_type,
                    size_bytes=artifact.size_bytes,
                    sha256=artifact.sha256,
                    expires_at=artifact.expires_at,
                )
                await success_session.commit()
            await message.ack()
        except Exception:
            # A database/broker outage must leave the delivery unacked so
            # RabbitMQ can redeliver it after the worker reconnects.
            await message.reject(requeue=True)


async def housekeeping_once(
    *,
    session_factory: SessionFactory,
    publisher: Any,
    stale_after_seconds: int,
    minio_delete: Callable[[str], Awaitable[None]] | None = None,
) -> None:
    """Republish unpublished jobs, converge stale workers and expire objects."""
    async with session_factory() as session:
        repository = DownloadRepository(session)
        unpublished = await repository.list_unpublished_jobs()
        for job in unpublished:
            try:
                await publisher.publish(job.id)
            except Exception:
                continue
            await repository.mark_published(job.id)
        await repository.collect_stale_running(
            stale_after=timedelta(seconds=stale_after_seconds)
        )
        expired_keys = await repository.expire_artifacts()
        await session.commit()

    if minio_delete is not None:
        for object_key in expired_keys:
            try:
                await minio_delete(object_key)
            except Exception:
                # MinIO lifecycle is the physical-deletion fallback; the DB
                # tombstone is already durable and must not be rolled back.
                continue


async def run_worker(
    settings: Any, session_factory: SessionFactory, processor: DownloadProcessor
) -> None:
    """Run the long-lived direct RabbitMQ consumer until cancelled."""
    topology = RabbitMQTopology.from_settings(settings)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        _, queue = await declare_topology(channel, topology)
        consumer = WorkerConsumer(session_factory=session_factory, processor=processor)
        await queue.consume(consumer.handle_message, no_ack=False)
        await asyncio.Future()
    finally:
        await connection.close()


async def main() -> None:
    """Worker process entry point with RabbitMQ and housekeeping."""
    from src.core.config import get_settings
    from src.db.session import get_session_factory

    settings = get_settings()
    session_factory = cast(SessionFactory, get_session_factory())
    processor = DefaultDownloadProcessor(settings, session_factory)
    publisher = RabbitMQPublisher(settings)
    await publisher.connect()
    worker_task = asyncio.create_task(run_worker(settings, session_factory, processor))
    try:
        while True:
            await asyncio.sleep(settings.housekeeping_interval_seconds)
            await housekeeping_once(
                session_factory=session_factory,
                publisher=publisher,
                stale_after_seconds=settings.running_stale_after_seconds,
                minio_delete=processor.storage.remove,
            )
    finally:
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
        await publisher.close()


if __name__ == "__main__":  # pragma: no cover - exercised by the container
    asyncio.run(main())
