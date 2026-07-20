from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
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
