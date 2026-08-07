from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from app.runner.errors import RunnerFailure
from app.runner.process import ProcessResult
from app.runner.service import MediaRunnerService
from helpers import download_request, result, settings, split_media_info


class ThumbnailStream:
    status_code = 200
    headers = {"content-type": "image/jpeg", "content-length": "5"}
    is_redirect = False

    async def __aenter__(self) -> ThumbnailStream:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def aiter_bytes(self):
        yield b"cover"


class ThumbnailClient:
    def __init__(self, **kwargs: object) -> None:
        self.options = kwargs
        self.requests: list[tuple[str, str]] = []

    async def __aenter__(self) -> ThumbnailClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def stream(self, method: str, url: str, **_: object) -> ThumbnailStream:
        self.requests.append((method, url))
        return ThumbnailStream()


class FixtureSupervisor:
    def __init__(self, info: dict[str, object]) -> None:
        self.info = info
        self.calls: list[tuple[tuple[str, ...], Mapping[str, str] | None]] = []

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        command = tuple(argv)
        self.calls.append((command, env))
        if "--dump-single-json" in command:
            return result(json.dumps(self.info).encode())
        if command[0] == "yt-dlp":
            output = Path(command[command.index("--output") + 1])
            output.write_bytes(b"downloaded-stream")
            return result()
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"final-media")
            return result()
        if command[0] == "ffprobe":
            probe = {
                "format": {"format_name": "mov,mp4,m4a", "duration": "30"},
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 1920,
                        "height": 1080,
                        "avg_frame_rate": "30/1",
                    },
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
            }
            return result(json.dumps(probe).encode())
        raise AssertionError(command)


class ProbeSampleSupervisor(FixtureSupervisor):
    def __init__(self, info: dict[str, object]) -> None:
        super().__init__(info)
        self.inspection_attempts = 0

    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        command = tuple(argv)
        if "--dump-single-json" in command:
            self.inspection_attempts += 1
            if self.inspection_attempts == 1:
                self.calls.append((command, env))
                return ProcessResult(1, b"", b"transient", False, False)
        if command[0] == "ffprobe" and str(command[-1]).startswith("https://"):
            self.calls.append((command, env))
            return ProcessResult(1, b"", b"forbidden", False, False)
        return await super().run(
            argv,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            env=env,
        )


async def test_download_reinspects_selects_semantics_and_verifies_artifact(
    tmp_path: Path,
) -> None:
    supervisor = FixtureSupervisor(split_media_info())
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    response = await service.download(download_request())

    artifact = Path(response.workspace_path) / response.artifact.relative_path
    assert artifact.read_bytes() == b"final-media"
    assert response.artifact.sha256 == hashlib.sha256(b"final-media").hexdigest()
    commands = [call[0] for call in supervisor.calls]
    ytdlp = [command for command in commands if command[0] == "yt-dlp"]
    assert all("http://egress-proxy:3128" in command for command in ytdlp)
    assert all("--plugin-dirs" in command for command in ytdlp)
    assert all("--cookies" in command for command in ytdlp)
    assert all(
        Path(command[command.index("--cookies") + 1]).name
        == "provider-cookies.txt"
        for command in ytdlp
    )
    assert all(
        command[command.index("--js-runtimes") + 1] == "node"
        for command in ytdlp
    )
    plugin_root = Path(ytdlp[0][ytdlp[0].index("--plugin-dirs") + 1])
    assert (plugin_root / "plugins/yt_dlp_plugins/extractor/mediatrack.py").is_file()
    assert [command[command.index("--format") + 1] for command in ytdlp[1:]] == [
        "video",
        "audio",
    ]
    ffmpeg = next(command for command in commands if command[0] == "ffmpeg")
    assert "copy" in ffmpeg
    assert ffmpeg[ffmpeg.index("-protocol_whitelist") + 1] == "file,crypto,data"
    ffprobe = next(command for command in commands if command[0] == "ffprobe")
    assert ffprobe[ffprobe.index("-protocol_whitelist") + 1] == "file,crypto,data"
    assert all("RUNNER_HMAC_SECRET" not in (env or {}) for _, env in supervisor.calls)
    status = await service.status("job_123")
    assert status.stage.value == "ready"
    assert status.progress == 100


async def test_download_never_downgrades_and_cleans_failed_workspace(
    tmp_path: Path,
) -> None:
    supervisor = FixtureSupervisor(split_media_info(height=720))
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    with pytest.raises(RunnerFailure) as caught:
        await service.download(download_request())

    assert caught.value.code == "format_unavailable"
    assert list(tmp_path.iterdir()) == []


async def test_download_rejects_source_identity_drift_before_download(
    tmp_path: Path,
) -> None:
    changed = split_media_info()
    changed["id"] = "different-media"
    supervisor = FixtureSupervisor(changed)
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    with pytest.raises(RunnerFailure) as caught:
        await service.download(download_request())

    assert caught.value.code == "source_changed"
    assert len(supervisor.calls) == 1
    assert list(tmp_path.iterdir()) == []


async def test_inspect_requires_at_least_one_semantic_option(tmp_path: Path) -> None:
    info = split_media_info()
    formats = info["formats"]
    assert isinstance(formats, list)
    info["formats"] = formats[:1]
    supervisor = FixtureSupervisor(info)
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    with pytest.raises(RunnerFailure) as caught:
        await service.inspect("https://media.example.com/video")

    assert caught.value.code == "format_unavailable"


async def test_inspect_enriches_sparse_provider_formats_with_bounded_probe(
    tmp_path: Path,
) -> None:
    info = split_media_info()
    info["formats"] = [
        {
            "format_id": "http-832",
            "ext": "mp4",
            "url": "https://cdn.example.com/video.mp4",
        }
    ]
    supervisor = FixtureSupervisor(info)
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    response = await service.inspect("https://media.example.com/video")

    assert response.streams[0].height == 1080
    ffprobe = next(
        command
        for command, _ in supervisor.calls
        if command[0] == "ffprobe" and str(command[-1]).startswith("https://")
    )
    assert ffprobe[-1] == "https://cdn.example.com/video.mp4"
    assert (
        ffprobe[ffprobe.index("-protocol_whitelist") + 1]
        == "http,https,tcp,tls,crypto,httpproxy"
    )


async def test_inspect_recovers_missing_duration_from_sparse_probe(
    tmp_path: Path,
) -> None:
    info = split_media_info()
    info["duration"] = None
    info["formats"] = [
        {
            "format_id": "http-832",
            "ext": "mp4",
            "url": "https://cdn.example.com/video.mp4",
        }
    ]
    supervisor = FixtureSupervisor(info)
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    response = await service.inspect("https://media.example.com/video")

    assert response.media.duration_seconds == 30
    assert response.streams[0].video_codec_family.value == "h264"


async def test_inspect_retries_and_uses_bounded_local_probe_sample(
    tmp_path: Path,
) -> None:
    info = split_media_info()
    info["formats"] = [
        {
            "format_id": "h264-540p",
            "ext": "mp4",
            "width": 576,
            "height": 1024,
            "vcodec": "h264",
            "acodec": "aac",
            "filesize": 1_300_000,
            "url": "https://cdn.example.com/video.mp4",
        }
    ]
    supervisor = ProbeSampleSupervisor(info)
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    response = await service.inspect("https://media.example.com/video")

    assert supervisor.inspection_attempts == 2
    assert response.streams[0].fps == 30
    sample = next(
        command
        for command, _ in supervisor.calls
        if command[0] == "yt-dlp" and "--max-filesize" in command
    )
    assert sample[sample.index("--max-filesize") + 1] == str(8 * 1024**2)
    assert not (tmp_path / "format-probe.input").exists()


async def test_inspect_fetches_a_bounded_thumbnail_through_the_proxy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = split_media_info()
    info["thumbnail"] = "https://images.example.com/cover.jpg"
    supervisor = FixtureSupervisor(info)
    clients: list[ThumbnailClient] = []

    def client_factory(**kwargs: object) -> ThumbnailClient:
        client = ThumbnailClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr("app.runner.service.httpx.AsyncClient", client_factory)
    service = MediaRunnerService(settings(tmp_path), supervisor=supervisor)

    response = await service.inspect("https://media.example.com/video")

    assert response.media.thumbnail_data_url == "data:image/jpeg;base64,Y292ZXI="
    assert clients[0].options["proxy"] == "http://egress-proxy:3128"
    assert clients[0].requests == [("GET", "https://images.example.com/cover.jpg")]
