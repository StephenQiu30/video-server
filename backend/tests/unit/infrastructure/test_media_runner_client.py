from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from app.application.downloads.errors import MediaInspectionAccessRequired
from app.infrastructure.media_runner import MediaRunnerHttpClient
from app.runner.contracts import DownloadPlanContract


@pytest.mark.asyncio
async def test_inspect_exposes_provider_access_requirement() -> None:
    async def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "error": {
                    "code": "provider_access_required",
                    "message": "provider access required",
                }
            },
        )

    http = httpx.AsyncClient(
        base_url="http://runner",
        transport=httpx.MockTransport(respond),
    )
    client = MediaRunnerHttpClient(
        base_url="http://runner",
        secret=b"s" * 32,
        workspace_root=Path("."),
        inspect_timeout_seconds=1,
        download_timeout_seconds=1,
        client=http,
    )

    with pytest.raises(MediaInspectionAccessRequired):
        await client.inspect("https://www.douyin.com/video/123")

    await http.aclose()


@pytest.mark.asyncio
async def test_download_sends_expected_inspection_identity(tmp_path) -> None:
    captured: dict[str, object] = {}
    workspace = tmp_path / "job-controlled"

    async def respond(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "task_id": "job_123",
                "workspace_path": str(workspace),
                "artifact": {
                    "relative_path": "artifact.mp4",
                    "size_bytes": 5,
                    "sha256": "a" * 64,
                    "duration_seconds": 30,
                    "container": "mp4",
                    "video_streams": 1,
                    "audio_streams": 1,
                },
                "selection": None,
            },
        )

    http = httpx.AsyncClient(
        base_url="http://runner",
        transport=httpx.MockTransport(respond),
    )
    client = MediaRunnerHttpClient(
        base_url="http://runner",
        secret=b"s" * 32,
        workspace_root=tmp_path,
        inspect_timeout_seconds=1,
        download_timeout_seconds=1,
        client=http,
    )
    plan = DownloadPlanContract.model_validate(
        {
            "height": 720,
            "width": 1280,
            "fps_bucket": "fps_30",
            "dynamic_range": "sdr",
            "video_codec_family": "h264",
            "audio_codec_family": "aac",
            "audio_language": None,
            "container_preference": "mp4",
            "compatibility_profile": "balanced",
            "hints": {"video_id": "v1", "audio_id": "a1"},
        }
    ).to_domain()

    await client.download(
        "job_123",
        "https://media.example/video",
        plan,
        expected_provider_media_id="video-1",
        expected_extractor_key="Controlled",
    )

    assert captured["expected_provider_media_id"] == "video-1"
    assert captured["expected_extractor_key"] == "Controlled"
    await http.aclose()
