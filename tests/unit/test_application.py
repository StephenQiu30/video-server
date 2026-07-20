from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from src.core.errors import AppError
from src.downloads.application import DownloadApplicationService


class Session:
    def __init__(self, scalar_value: object = None) -> None:
        self.scalar_value = scalar_value
        self.commits = 0

    async def __aenter__(self) -> Session:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def scalar(self, *_: object) -> object:
        return self.scalar_value

    async def commit(self) -> None:
        self.commits += 1


def service(
    session: Session, repository: object | None = None
) -> tuple[DownloadApplicationService, object]:
    storage = SimpleNamespace(
        presigned_download=AsyncMock(return_value="https://minio/object")
    )
    settings = SimpleNamespace(minio_presigned_url_ttl_seconds=60)
    app = DownloadApplicationService(lambda **_: session, storage, settings)
    return app, storage


def job(status: str = "succeeded", *, expired: bool = False) -> SimpleNamespace:
    now = datetime.now(UTC)
    artifact = SimpleNamespace(
        object_key="jobs/object.mp4",
        file_name="video.mp4",
        deleted_at=None,
        expires_at=now + timedelta(hours=1)
        if not expired
        else now - timedelta(seconds=1),
    )
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        source_id=uuid.uuid4(),
        format_id=uuid.uuid4(),
        artifact=artifact if status == "succeeded" else None,
    )


@pytest.mark.asyncio
async def test_create_download_idempotency_and_expired_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_id = uuid.uuid4()
    format_id = uuid.uuid4()
    request_id = uuid.uuid4()
    existing = job()
    existing.source_id = source_id
    existing.format_id = format_id
    session = Session(existing)
    app, _ = service(session)
    repository = SimpleNamespace()
    monkeypatch.setattr(
        "src.downloads.application.DownloadRepository", lambda _: repository
    )
    replay, created = await app.create_download(
        owner_token_hash="owner",
        source_id=source_id,
        format_id=format_id,
        client_request_id=request_id,
    )
    assert replay is existing and not created and session.commits == 0
    with pytest.raises(AppError) as raised:
        await app.create_download(
            owner_token_hash="owner",
            source_id=uuid.uuid4(),
            format_id=format_id,
            client_request_id=request_id,
        )
    assert raised.value.code == "IDEMPOTENCY_CONFLICT"

    session = Session(None)
    created_job = job("queued")
    repository.add_job = AsyncMock(return_value=created_job)
    monkeypatch.setattr(
        "src.downloads.application.DownloadRepository", lambda _: repository
    )
    app, _ = service(session)
    result, is_created = await app.create_download(
        owner_token_hash="owner",
        source_id=source_id,
        format_id=format_id,
        client_request_id=request_id,
    )
    assert result is created_job and is_created and session.commits == 1
    repository.add_job = AsyncMock(side_effect=RuntimeError("media inspection expired"))
    with pytest.raises(AppError) as raised:
        await app.create_download(
            owner_token_hash="owner",
            source_id=source_id,
            format_id=format_id,
            client_request_id=uuid.uuid4(),
        )
    assert raised.value.code == "INSPECTION_EXPIRED"


@pytest.mark.asyncio
async def test_get_download_and_presigned_url_state_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SimpleNamespace(get_job=AsyncMock())
    monkeypatch.setattr(
        "src.downloads.application.DownloadRepository", lambda _: repository
    )
    session = Session()
    app, storage = service(session)
    found = job()
    repository.get_job.return_value = found
    assert await app.get_download(owner_token_hash="owner", job_id=found.id) is found
    repository.get_job.side_effect = LookupError("not found")
    with pytest.raises(AppError) as raised:
        await app.get_download(owner_token_hash="owner", job_id=found.id)
    assert raised.value.code == "RESOURCE_NOT_FOUND"

    for candidate, code in (
        (job("expired"), "JOB_EXPIRED"),
        (job("queued"), "JOB_NOT_READY"),
        (job("succeeded", expired=True), "JOB_EXPIRED"),
    ):
        repository.get_job.side_effect = None
        repository.get_job.return_value = candidate
        with pytest.raises(AppError) as raised:
            await app.create_download_url(owner_token_hash="owner", job_id=candidate.id)
        assert raised.value.code == code

    ready = job()
    repository.get_job.return_value = ready
    result = await app.create_download_url(owner_token_hash="owner", job_id=ready.id)
    assert (
        result["url"] == "https://minio/object" and result["file_name"] == "video.mp4"
    )
    storage.presigned_download.assert_awaited_once()
    assert storage.presigned_download.call_args.kwargs["expires_seconds"] == 60
