from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from src.api.router import router
from src.downloads.service import DownloadService
from src.media.formats import NormalizedFormat
from src.media.service import MediaInspectionService
from src.media.yt_dlp import InspectResult


class Session:
    def __init__(self) -> None:
        self.commits = 0

    async def __aenter__(self) -> Session:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_download_service_delegates_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SimpleNamespace(
        add_source=AsyncMock(return_value="source"),
        add_job=AsyncMock(return_value="job"),
        transition=AsyncMock(return_value="transition"),
        succeed_with_artifact=AsyncMock(return_value="artifact"),
    )
    monkeypatch.setattr(
        "src.downloads.service.DownloadRepository", lambda _: repository
    )
    service = DownloadService(SimpleNamespace())
    assert await service.inspect_source(source_url="url") == "source"
    source_id, format_id, request_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    assert (
        await service.create_job(
            owner_token_hash="owner",
            client_request_id=request_id,
            source_id=source_id,
            format_id=format_id,
        )
        == "job"
    )
    assert await service.transition(uuid.uuid4(), stage="downloading") == "transition"
    assert await service.succeed(uuid.uuid4(), object_key="key") == "artifact"
    repository.add_source.assert_awaited_once()
    repository.add_job.assert_awaited_once()
    repository.transition.assert_awaited_once()
    repository.succeed_with_artifact.assert_awaited_once()
    assert len(router.routes) == 3


@pytest.mark.asyncio
async def test_media_inspection_service_persists_normalized_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fmt = NormalizedFormat(
        video_format_id="18",
        audio_format_id=None,
        label="360p",
        width=640,
        height=360,
        fps=None,
        container="mp4",
        video_codec="avc1",
        audio_codec="mp4a",
        estimated_size_bytes=10,
        requires_merge=False,
    )
    result = InspectResult(
        source_url="https://example.test/video",
        extractor_key="example",
        external_id="id",
        title="Title",
        thumbnail_url=None,
        duration_seconds=10,
        formats=(fmt,),
    )
    repository = SimpleNamespace(add_source=AsyncMock(return_value="source"))
    monkeypatch.setattr("src.media.service.DownloadRepository", lambda _: repository)
    session = Session()
    service = MediaInspectionService(
        lambda **_: session,
        SimpleNamespace(inspect_async=AsyncMock(return_value=result)),
        inspect_ttl_seconds=30,
    )
    assert (
        await service.inspect_media(
            url="https://example.test/video", owner_token_hash="h" * 64
        )
        == "source"
    )
    assert session.commits == 1
    kwargs = repository.add_source.call_args.kwargs
    assert kwargs["source_host"] == "example.test"
    assert kwargs["formats"][0]["video_format_id"] == "18"
