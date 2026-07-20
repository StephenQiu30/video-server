from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from src.downloads.state import JobStatus
from src.media.ffprobe import ProbeResult
from src.worker import (
    ArtifactPayload,
    DefaultDownloadProcessor,
    WorkerConsumer,
    housekeeping_once,
    run_worker,
)


class Session:
    def __init__(self, *, fail_commit: bool = False) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = fail_commit

    async def __aenter__(self) -> Session:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("database unavailable")
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class Message:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.acks = 0
        self.rejects: list[bool] = []

    async def ack(self) -> None:
        self.acks += 1

    async def reject(self, *, requeue: bool) -> None:
        self.rejects.append(requeue)


def message(job_id: uuid.UUID) -> Message:
    return Message(b'{"job_id":"' + str(job_id).encode() + b'"}')


def fake_job(status: str = JobStatus.QUEUED.value) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        source=SimpleNamespace(source_url="https://example.test/video", title="title"),
        format=SimpleNamespace(
            video_format_id="bestvideo",
            audio_format_id="bestaudio",
            label="720p",
            width=1280,
            height=720,
            fps=None,
            container="mp4",
            video_codec="avc1",
            audio_codec="mp4a",
            estimated_size_bytes=100,
            requires_merge=False,
            sort_order=0,
        ),
    )


def payload() -> ArtifactPayload:
    return ArtifactPayload(
        object_key="jobs/object.mp4",
        file_name="video.mp4",
        content_type="video/mp4",
        size_bytes=10,
        sha256="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


class Repo:
    def __init__(self, job: SimpleNamespace | None = None) -> None:
        self.job = job
        self.transitions: list[tuple[object, ...]] = []
        self.succeeded = False

    async def get_worker_job(self, *_: object, **__: object) -> SimpleNamespace | None:
        return self.job

    async def transition(self, *args: object, **kwargs: object) -> None:
        self.transitions.append((*args, *kwargs.values()))

    async def succeed_with_artifact(self, *_: object, **__: object) -> None:
        self.succeeded = True

    async def list_unpublished_jobs(self) -> list[SimpleNamespace]:
        return []

    async def mark_published(self, *_: object, **__: object) -> bool:
        return True

    async def collect_stale_running(self, **_: object) -> list[uuid.UUID]:
        return []

    async def expire_artifacts(self, **_: object) -> list[str]:
        return []


@pytest.mark.asyncio
async def test_worker_consumer_rejects_bad_and_acknowledges_terminal_or_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = Repo()
    monkeypatch.setattr("src.worker.DownloadRepository", lambda _: repo)
    session = Session()

    def factory(**_: object) -> Session:
        return session

    consumer = WorkerConsumer(factory, AsyncMock())
    bad = Message(b"not-json")
    await consumer.handle_message(bad)
    assert bad.rejects == [False]

    for status in (
        JobStatus.SUCCEEDED.value,
        JobStatus.FAILED.value,
        JobStatus.EXPIRED.value,
        JobStatus.RUNNING.value,
    ):
        repo.job = fake_job(status)
        msg = message(repo.job.id)
        await consumer.handle_message(msg)
        assert msg.acks == 1


@pytest.mark.asyncio
async def test_worker_consumer_success_and_failure_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = Repo(fake_job())
    monkeypatch.setattr("src.worker.DownloadRepository", lambda _: repo)

    def factory(**_: object) -> Session:
        return Session()

    processor = AsyncMock(return_value=payload())
    consumer = WorkerConsumer(factory, processor)
    msg = message(repo.job.id)
    await consumer.handle_message(msg)
    assert msg.acks == 1 and repo.succeeded
    assert repo.transitions and repo.transitions[0][-1] == JobStatus.RUNNING

    repo = Repo(fake_job())
    monkeypatch.setattr("src.worker.DownloadRepository", lambda _: repo)
    failed = WorkerConsumer(
        factory, AsyncMock(side_effect=RuntimeError("download failed"))
    )
    msg = message(repo.job.id)
    await failed.handle_message(msg)
    assert msg.acks == 1 and not msg.rejects
    assert repo.transitions and repo.transitions[0][-1] == JobStatus.RUNNING
    assert repo.transitions[-1][2] == JobStatus.FAILED

    # A transaction/broker failure is left for RabbitMQ redelivery.
    monkeypatch.setattr(
        "src.worker.DownloadRepository",
        lambda _: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    msg = message(uuid.uuid4())
    await WorkerConsumer(factory, AsyncMock()).handle_message(msg)
    assert msg.rejects == [True]


@pytest.mark.asyncio
async def test_housekeeping_republishes_and_deletes_expired_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = SimpleNamespace(id=uuid.uuid4())
    repo = Repo()
    repo.expire_artifacts = AsyncMock(return_value=["expired.mp4"])
    repo.list_unpublished_jobs = AsyncMock(return_value=[job])
    monkeypatch.setattr("src.worker.DownloadRepository", lambda _: repo)
    publisher = SimpleNamespace(publish=AsyncMock())
    removed = AsyncMock()
    await housekeeping_once(
        session_factory=lambda **_: Session(),
        publisher=publisher,
        stale_after_seconds=10,
        minio_delete=removed,
    )
    publisher.publish.assert_awaited_once_with(job.id)
    removed.assert_awaited_once_with("expired.mp4")

    publisher.publish = AsyncMock(side_effect=RuntimeError("broker down"))
    removed = AsyncMock(side_effect=RuntimeError("minio down"))
    await housekeeping_once(
        session_factory=lambda **_: Session(),
        publisher=publisher,
        stale_after_seconds=10,
        minio_delete=removed,
    )


@pytest.mark.asyncio
async def test_run_worker_declares_consumer_and_closes_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Queue:
        def __init__(self) -> None:
            self.callback = None

        async def consume(self, callback: object, *, no_ack: bool) -> None:
            self.callback = callback
            assert no_ack is False

    class Connection:
        def __init__(self) -> None:
            self.closed = False
            self.queue = Queue()

        async def channel(self) -> object:
            return object()

        async def close(self) -> None:
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(
        "src.worker.aio_pika.connect_robust", AsyncMock(return_value=connection)
    )
    monkeypatch.setattr(
        "src.worker.declare_topology",
        AsyncMock(return_value=(object(), connection.queue)),
    )
    settings = SimpleNamespace(
        rabbitmq_url="amqp://localhost/",
        rabbitmq_exchange="video",
        rabbitmq_queue="queue",
        rabbitmq_routing_key="download",
        rabbitmq_prefetch_count=1,
    )
    task = asyncio.create_task(run_worker(settings, lambda **_: Session(), AsyncMock()))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert connection.closed


@pytest.mark.asyncio
async def test_default_processor_downloads_and_uploads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    job = fake_job()
    repo = Repo(job)
    monkeypatch.setattr("src.worker.DownloadRepository", lambda _: repo)

    class Storage:
        def __init__(self, _: object) -> None:
            self.uploads: list[tuple[str, Path]] = []

        async def put_file(self, key: str, path: Path, **_: object) -> None:
            self.uploads.append((key, path))

    class Downloader:
        def __init__(self, **_: object) -> None:
            pass

        def download_to_workspace(self, **kwargs: object) -> SimpleNamespace:
            workspace = kwargs["workspace"]
            assert isinstance(workspace, Path)
            path = workspace / "artifact.mp4"
            path.write_bytes(b"video")
            return SimpleNamespace(
                path=path,
                file_name="title.mp4",
                content_type="video/mp4",
                size_bytes=5,
                sha256="b" * 64,
                probe=ProbeResult(
                    "mp4", 1.0, ({"codec_type": "video"}, {"codec_type": "audio"})
                ),
            )

    monkeypatch.setattr("src.worker.MinioStorage", Storage)
    monkeypatch.setattr("src.worker.MediaDownloader", Downloader)
    settings = SimpleNamespace(
        worker_temp_dir=tmp_path,
        download_timeout_seconds=10,
        max_file_size_bytes=100,
        max_video_duration_seconds=10,
        artifact_ttl_seconds=60,
    )
    processor = DefaultDownloadProcessor(settings, lambda **_: Session())
    result = await processor(job.id)
    assert result.file_name == "title.mp4"
    assert result.object_key.startswith(f"jobs/{job.id}/")
