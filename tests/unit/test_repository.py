from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from src.downloads.repository import (
    DownloadRepository,
    NotFoundError,
    RepositoryConflict,
)
from src.downloads.state import JobStatus


class Result:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount


class Session:
    def __init__(
        self,
        *,
        scalar_values: list[object] | None = None,
        scalars_values: list[list[object]] | None = None,
        execute_rowcounts: list[int] | None = None,
    ) -> None:
        self.scalar_values = list(scalar_values or [])
        self.scalars_values = list(scalars_values or [])
        self.execute_rowcounts = list(execute_rowcounts or [])
        self.added: list[object] = []
        self.flushed = 0
        self.rollbacks = 0

    async def scalar(self, *_: object) -> object:
        return self.scalar_values.pop(0) if self.scalar_values else None

    async def scalars(self, *_: object) -> list[object]:
        return self.scalars_values.pop(0) if self.scalars_values else []

    async def execute(self, *_: object) -> Result:
        return Result(self.execute_rowcounts.pop(0) if self.execute_rowcounts else 1)

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def source(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "source_id": uuid.uuid4(),
        "source_url": "https://example.test/video",
        "inspect_expires_at": datetime.now(UTC) + timedelta(hours=1),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def worker_job(status: str = "running") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        source_id=uuid.uuid4(),
        source=source(),
        artifact=None,
    )


@pytest.mark.asyncio
async def test_add_source_and_job_validation_and_replay() -> None:
    session = Session(scalar_values=[None, source(), SimpleNamespace(id=uuid.uuid4())])
    repository = DownloadRepository(session)
    result = await repository.add_source(
        owner_token_hash="h" * 64,
        source_url="https://example.test/video",
        source_host="example.test",
        extractor_key="example",
        title="title",
        inspect_expires_at=datetime.now(UTC) + timedelta(minutes=1),
        formats=[
            {
                "video_format_id": "18",
                "audio_format_id": None,
                "label": "360p",
                "width": 640,
                "height": 360,
                "fps": None,
                "container": "mp4",
                "video_codec": "avc1",
                "audio_codec": "mp4a",
                "estimated_size_bytes": 10,
                "requires_merge": False,
                "sort_order": 0,
            }
        ],
    )
    assert result in session.added and session.flushed == 1

    with pytest.raises(NotFoundError):
        await DownloadRepository(Session(scalar_values=[None])).get_source(
            "owner", uuid.uuid4()
        )

    source_row = source()
    fmt = SimpleNamespace(id=uuid.uuid4())
    loaded_job = worker_job(JobStatus.QUEUED.value)
    session = Session(scalar_values=[None, source_row, fmt, loaded_job])
    repository = DownloadRepository(session)
    job = await repository.add_job(
        owner_token_hash="h" * 64,
        client_request_id=uuid.uuid4(),
        source_id=source_row.id,
        format_id=fmt.id,
    )
    assert job is loaded_job and job.status == JobStatus.QUEUED.value

    replay = source()
    replay.source_id = source_row.id
    replay.format_id = fmt.id
    session = Session(scalar_values=[replay])
    result = await DownloadRepository(session).add_job(
        owner_token_hash="h" * 64,
        client_request_id=uuid.uuid4(),
        source_id=source_row.id,
        format_id=fmt.id,
    )
    assert result is replay
    replay.source_id = uuid.uuid4()
    with pytest.raises(RepositoryConflict):
        await DownloadRepository(Session(scalar_values=[replay])).add_job(
            owner_token_hash="h" * 64,
            client_request_id=uuid.uuid4(),
            source_id=source_row.id,
            format_id=fmt.id,
        )


@pytest.mark.asyncio
async def test_repository_updates_and_artifact_lifecycle() -> None:
    job = worker_job()
    session = Session(scalar_values=[job], execute_rowcounts=[1])
    repository = DownloadRepository(session)
    assert await repository.mark_published(job.id)
    assert not await DownloadRepository(Session(execute_rowcounts=[0])).mark_published(
        job.id
    )

    session = Session(scalar_values=[job], execute_rowcounts=[1, 1])
    updated = await DownloadRepository(session).transition(
        job.id,
        expected=JobStatus.RUNNING,
        target=JobStatus.SUCCEEDED,
        stage="uploading",
        progress_percent=100,
        downloaded_bytes=10,
        total_bytes=10,
        error_code="done",
        error_message="ok",
    )
    assert updated is job and len(session.execute_rowcounts) == 0
    with pytest.raises(ValueError):
        await DownloadRepository(Session()).transition(
            job.id,
            expected=JobStatus.RUNNING,
            target=JobStatus.SUCCEEDED,
            progress_percent=101,
        )
    assert await DownloadRepository(Session(execute_rowcounts=[1])).touch_heartbeat(
        job.id
    )
    assert not await DownloadRepository(Session(execute_rowcounts=[0])).touch_heartbeat(
        job.id
    )
    assert await DownloadRepository(Session(execute_rowcounts=[1])).update_progress(
        job.id,
        stage="downloading",
        progress_percent=10,
        downloaded_bytes=2,
        total_bytes=20,
    )
    with pytest.raises(ValueError):
        await DownloadRepository(Session()).update_progress(
            job.id, stage="downloading", progress_percent=101
        )

    success_job = worker_job(JobStatus.RUNNING.value)
    session = Session(scalar_values=[success_job], execute_rowcounts=[1, 1])
    artifact = await DownloadRepository(session).succeed_with_artifact(
        success_job.id,
        object_key="jobs/a.mp4",
        file_name="a.mp4",
        content_type="video/mp4",
        size_bytes=10,
        sha256="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    assert artifact in session.added
    with pytest.raises(RepositoryConflict):
        await DownloadRepository(
            Session(scalar_values=[worker_job(JobStatus.QUEUED.value)])
        ).succeed_with_artifact(
            uuid.uuid4(),
            object_key="jobs/b.mp4",
            file_name="b.mp4",
            content_type="video/mp4",
            size_bytes=10,
            sha256="b" * 64,
            expires_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_repository_queries_recovery_and_expiry() -> None:
    first, second = worker_job(), worker_job()
    session = Session(scalars_values=[[first, second], [uuid.uuid4()]])
    repository = DownloadRepository(session)
    assert await repository.list_unpublished_jobs() == [first, second]
    assert (
        len(await repository.collect_stale_running(stale_after=timedelta(minutes=1)))
        == 1
    )

    artifact = SimpleNamespace(
        object_key="jobs/expired.mp4",
        download_job_id=uuid.uuid4(),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        deleted_at=None,
    )
    session = Session(scalars_values=[[artifact]], execute_rowcounts=[1])
    keys = await DownloadRepository(session).expire_artifacts()
    assert keys == ["jobs/expired.mp4"] and artifact.deleted_at is not None
    assert (
        await DownloadRepository(Session(execute_rowcounts=[3])).purge_metadata(
            older_than=datetime.now(UTC)
        )
        == 3
    )

    missing = Session(scalar_values=[None])
    with pytest.raises(NotFoundError):
        await DownloadRepository(missing).get_job("owner", uuid.uuid4())
    assert (
        await DownloadRepository(Session(scalar_values=[None])).get_worker_job(
            uuid.uuid4()
        )
        is None
    )
