from __future__ import annotations

from pathlib import Path

import pytest
from src.media.download import (
    DownloadLimits,
    MediaDownloader,
    MediaDownloadError,
    MediaSizeLimitError,
)
from src.media.ffprobe import ProbeResult
from src.media.formats import NormalizedFormat
from src.media.url_policy import URLPolicy

FORMAT = NormalizedFormat(
    video_format_id="v",
    audio_format_id=None,
    label="360p",
    width=640,
    height=360,
    fps=30,
    container="mp4",
    video_codec="avc1",
    audio_codec="mp4a",
    estimated_size_bytes=10,
    requires_merge=False,
)


class Client:
    error: Exception | None = None
    write = True
    options: dict[str, object] | None = None

    def __init__(self, options: dict[str, object]) -> None:
        self.__class__.options = options

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def download(self, urls: list[str]) -> None:
        assert urls == ["https://example.test/video"]
        if self.error is not None:
            raise self.error
        if self.write:
            output = Path(str(self.options["outtmpl"]).replace("%(ext)s", "mp4"))
            output.write_bytes(b"video")


def downloader(tmp_path: Path, **kwargs: object) -> MediaDownloader:
    limits = DownloadLimits(
        max_size_bytes=100, max_duration_seconds=10, temp_dir=tmp_path
    )
    return MediaDownloader(
        limits=limits,
        ytdlp_class=Client,
        policy=URLPolicy(resolver=lambda *_: ["8.8.8.8"]),
        **kwargs,
    )


def test_download_success_options_and_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    Client.error = None
    Client.write = True
    monkeypatch.setattr(
        "src.media.download.probe_media",
        lambda *_args, **_kwargs: ProbeResult(
            "mp4", 1.0, ({"codec_type": "video"}, {"codec_type": "audio"})
        ),
    )
    monkeypatch.setattr("src.media.download.sha256_file", lambda *_: "a" * 64)
    result = downloader(tmp_path).download_to_workspace(
        source_url="https://example.test/video",
        format_option=FORMAT,
        title="A title",
        workspace=tmp_path,
    )
    assert result.path.name == "artifact.mp4" and result.sha256 == "a" * 64
    assert Client.options and Client.options["noplaylist"] is True
    with pytest.raises(MediaSizeLimitError):
        downloader(tmp_path)._progress_hook({"downloaded_bytes": 101})


def test_download_rejects_policy_client_empty_probe_and_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    invalid = MediaDownloader(
        ytdlp_class=Client, policy=URLPolicy(resolver=lambda *_: ["127.0.0.1"])
    )
    with pytest.raises(MediaDownloadError):
        invalid._download_files("https://example.test/video", FORMAT, tmp_path)
    Client.error = RuntimeError("provider")
    with pytest.raises(MediaDownloadError):
        downloader(tmp_path)._download_files(
            "https://example.test/video", FORMAT, tmp_path
        )
    Client.error = None
    Client.write = False
    with pytest.raises(MediaDownloadError):
        downloader(tmp_path)._download_files(
            "https://example.test/video", FORMAT, tmp_path
        )
    Client.write = True
    monkeypatch.setattr(
        "src.media.download.probe_media",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")),
    )
    with pytest.raises(MediaDownloadError):
        downloader(tmp_path).download_to_workspace(
            source_url="https://example.test/video",
            format_option=FORMAT,
            title="x",
            workspace=tmp_path,
        )
    monkeypatch.setattr(
        "src.media.download.probe_media",
        lambda *_args, **_kwargs: ProbeResult(
            "mp4", 100.0, ({"codec_type": "video"}, {"codec_type": "audio"})
        ),
    )
    with pytest.raises(MediaSizeLimitError):
        downloader(tmp_path).download_to_workspace(
            source_url="https://example.test/video",
            format_option=FORMAT,
            title="x",
            workspace=tmp_path,
        )
