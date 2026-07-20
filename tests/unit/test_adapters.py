from __future__ import annotations

import io
import json
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from src.media.ffmpeg import MediaMergeError, merge_streams
from src.media.ffprobe import MediaProbeError, probe_media
from src.media.formats import FormatPolicyError, normalize_formats
from src.media.url_policy import URLPolicy
from src.media.yt_dlp import (
    MediaExtractionError,
    MediaInspectTimeout,
    MediaLimitError,
    UnsupportedMediaError,
    YtdlpExtractor,
)
from src.minio_client import MinioStorage
from src.rabbitmq import (
    DownloadMessage,
    RabbitMQPublisher,
    RabbitMQTopology,
    declare_topology,
    publish_job,
)


def test_message_contract_and_topology() -> None:
    job_id = uuid.uuid4()
    message = DownloadMessage(job_id)
    assert DownloadMessage.from_bytes(message.to_bytes()).job_id == job_id
    for invalid in (
        b"{}",
        b"[]",
        b"not-json",
        b'{"job_id":"bad"}',
        b'{"job_id":"x","extra":1}',
    ):
        with pytest.raises(ValueError):
            DownloadMessage.from_bytes(invalid)
    cfg = SimpleNamespace(
        rabbitmq_exchange="exchange",
        rabbitmq_queue="queue",
        rabbitmq_routing_key="key",
        rabbitmq_prefetch_count=3,
    )
    assert RabbitMQTopology.from_settings(cfg) == RabbitMQTopology(
        "exchange", "queue", "key", 3
    )


@pytest.mark.asyncio
async def test_rabbitmq_declare_publish_and_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Queue:
        def __init__(self) -> None:
            self.bound = None

        async def bind(self, exchange: object, *, routing_key: str) -> None:
            self.bound = (exchange, routing_key)

    class Channel:
        def __init__(self) -> None:
            self.exchange = object()
            self.queue = Queue()
            self.qos = None

        async def declare_exchange(self, *_: object, **__: object) -> object:
            return self.exchange

        async def declare_queue(self, *_: object, **__: object) -> Queue:
            return self.queue

        async def set_qos(self, **kwargs: object) -> None:
            self.qos = kwargs

    channel = Channel()
    topology = RabbitMQTopology("exchange", "queue", "key", 2)
    exchange, queue = await declare_topology(channel, topology)
    assert exchange is channel.exchange and queue is channel.queue
    assert channel.qos == {"prefetch_count": 2}
    assert channel.queue.bound == (channel.exchange, "key")

    class Exchange:
        def __init__(self) -> None:
            self.messages = []

        async def publish(self, message: object, *, routing_key: str) -> None:
            self.messages.append((message, routing_key))

    exchange_obj = Exchange()
    job_id = uuid.uuid4()
    await publish_job(exchange_obj, topology, job_id)
    assert exchange_obj.messages[0][1] == "key"
    assert json.loads(exchange_obj.messages[0][0].body) == {"job_id": str(job_id)}

    class Connection:
        def __init__(self) -> None:
            self.channel_value = Channel()
            self.closed = False

        async def channel(self, **_: object) -> Channel:
            return self.channel_value

        async def close(self) -> None:
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(
        "src.rabbitmq.aio_pika.connect_robust", AsyncMock(return_value=connection)
    )
    cfg = SimpleNamespace(
        rabbitmq_url="amqp://localhost/",
        rabbitmq_exchange="exchange",
        rabbitmq_queue="queue",
        rabbitmq_routing_key="key",
        rabbitmq_prefetch_count=2,
    )
    publisher = RabbitMQPublisher(cfg)
    await publisher.connect()
    assert publisher.exchange is connection.channel_value.exchange
    # The lifecycle test above uses a channel stub; inject a publish-capable
    # exchange to exercise the publisher adapter's final delegation.
    publisher.exchange = exchange_obj
    await publisher.publish(job_id)
    await publisher.close()
    assert connection.closed and publisher.exchange is None
    with pytest.raises(RuntimeError):
        await publisher.publish(job_id)


class FakeMinio:
    instances: list[FakeMinio] = []

    def __init__(self, *_: object, **__: object) -> None:
        self.exists = False
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.__class__.instances.append(self)

    def bucket_exists(self, bucket: str) -> bool:
        self.calls.append(("bucket_exists", (bucket,), {}))
        return self.exists

    def make_bucket(self, bucket: str) -> None:
        self.calls.append(("make_bucket", (bucket,), {}))
        self.exists = True

    def put_object(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("put_object", args, kwargs))

    def presigned_get_object(self, *args: object, **kwargs: object) -> str:
        self.calls.append(("presigned_get_object", args, kwargs))
        return "http://localhost:9000/video-artifacts/object"

    def remove_object(self, *args: object, **kwargs: object) -> None:
        self.calls.append(("remove_object", args, kwargs))


@pytest.mark.asyncio
async def test_minio_storage_upload_presign_health_and_remove(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    FakeMinio.instances.clear()
    monkeypatch.setattr("src.minio_client.Minio", FakeMinio)
    cfg = SimpleNamespace(
        minio_secure=False,
        minio_bucket="video-artifacts",
        minio_endpoint="minio:9000",
        minio_public_endpoint="localhost:9000",
        minio_access_key="access",
        minio_secret_key="secret",
        minio_presigned_url_ttl_seconds=60,
    )
    storage = MinioStorage(cfg)
    assert await storage.healthcheck()
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")
    await storage.put_file("object", path, content_type="video/mp4")
    await storage.put_stream(
        "stream", io.BytesIO(b"stream"), size_bytes=6, content_type="video/mp4"
    )
    url = await storage.presigned_download(
        "object", expires_seconds=10, response_filename='video".mp4'
    )
    assert url.startswith("http://")
    await storage.remove("object")
    assert any(call[0] == "put_object" for call in FakeMinio.instances[0].calls)
    assert any(
        call[0] == "presigned_get_object" for call in FakeMinio.instances[1].calls
    )
    assert any(call[0] == "remove_object" for call in FakeMinio.instances[0].calls)

    class Broken(FakeMinio):
        def bucket_exists(self, _: str) -> bool:
            raise OSError("down")

    monkeypatch.setattr("src.minio_client.Minio", Broken)
    assert not await MinioStorage(cfg).healthcheck()


def completed(returncode: int = 0, stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def test_ffmpeg_and_ffprobe_success_and_failures(tmp_path: Path) -> None:
    output = tmp_path / "out.mp4"
    output.write_bytes(b"video")
    with patch("src.media.ffmpeg.subprocess.run", return_value=completed()) as run:
        assert merge_streams(tmp_path / "v.mp4", tmp_path / "a.m4a", output) == output
        assert run.call_args.kwargs["shell"] is False
    with patch("src.media.ffmpeg.subprocess.run", side_effect=OSError("missing")):
        with pytest.raises(MediaMergeError):
            merge_streams(Path("v"), Path("a"), Path("out"))
    with patch("src.media.ffmpeg.subprocess.run", return_value=completed(1)):
        with pytest.raises(MediaMergeError):
            merge_streams(Path("v"), Path("a"), Path("out"))

    stream_json = json.dumps(
        {
            "format": {"format_name": "mp4", "duration": "1.2"},
            "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
        }
    )
    with patch(
        "src.media.ffprobe.subprocess.run", return_value=completed(stdout=stream_json)
    ):
        result = probe_media(Path("out"))
    assert result.has_video and result.has_audio and result.duration_seconds == 1.2
    with patch("src.media.ffprobe.subprocess.run", return_value=completed(stdout="{}")):
        with pytest.raises(MediaProbeError):
            probe_media(Path("out"))
    with patch(
        "src.media.ffprobe.subprocess.run",
        side_effect=subprocess.TimeoutExpired("ffprobe", 1),
    ):
        with pytest.raises(MediaProbeError):
            probe_media(Path("out"))


class FakeYtdlp:
    info: object = None
    error: Exception | None = None
    options: dict[str, object] | None = None

    def __init__(self, options: dict[str, object]) -> None:
        self.__class__.options = options

    def __enter__(self) -> FakeYtdlp:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def extract_info(self, *_: object, **__: object) -> object:
        if self.error is not None:
            raise self.error
        return self.info


def valid_info() -> dict[str, object]:
    return {
        "extractor_key": "Example",
        "id": "abc",
        "title": "  A   title ",
        "duration": 12,
        "formats": [
            {
                "format_id": "18",
                "height": 360,
                "width": 640,
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "filesize": 100,
            }
        ],
    }


def test_ytdlp_adapter_options_normalization_and_errors() -> None:
    FakeYtdlp.info = valid_info()
    FakeYtdlp.error = None
    extractor = YtdlpExtractor(
        ytdlp_class=FakeYtdlp,
        max_duration_seconds=100,
        policy=URLPolicy(resolver=lambda *_: ["8.8.8.8"]),
    )
    result = extractor.inspect("https://example.test/video")
    assert result.extractor_key == "Example" and result.title == "A title"
    assert FakeYtdlp.options and FakeYtdlp.options["ignoreconfig"] is True
    assert extractor._normalize(result.source_url, valid_info()).formats
    for info, exc in (
        ({"extractor_key": "generic", "formats": []}, UnsupportedMediaError),
        (
            {"extractor_key": "x", "entries": [{"id": 1}], "formats": []},
            UnsupportedMediaError,
        ),
        ({"extractor_key": "x", "is_live": True, "formats": []}, UnsupportedMediaError),
        ({"extractor_key": "x", "has_drm": True, "formats": []}, UnsupportedMediaError),
        (
            {"extractor_key": "x", "duration": "bad", "formats": []},
            UnsupportedMediaError,
        ),
        ({"extractor_key": "x", "duration": 999, "formats": []}, MediaLimitError),
    ):
        with pytest.raises(exc):
            extractor._normalize("https://example.test/video", info)
    FakeYtdlp.info = None
    FakeYtdlp.error = TimeoutError("timeout")
    with pytest.raises(MediaInspectTimeout):
        extractor.inspect("https://example.test/video")
    FakeYtdlp.error = RuntimeError("provider")
    with pytest.raises(MediaExtractionError):
        extractor.inspect("https://example.test/video")
    with pytest.raises(UnsupportedMediaError):
        extractor.inspect("file:///tmp/video")


def test_normalize_formats_rejects_missing_and_pairs_audio() -> None:
    with pytest.raises(FormatPolicyError):
        normalize_formats({})
    with pytest.raises(FormatPolicyError):
        normalize_formats({"formats": [{"format_id": "a", "acodec": "aac"}]})
    result = normalize_formats(
        {
            "formats": [
                {
                    "format_id": "v",
                    "height": 720,
                    "width": 1280,
                    "ext": "mp4",
                    "vcodec": "avc1",
                    "acodec": "none",
                    "filesize": 50,
                },
                {
                    "format_id": "a",
                    "ext": "m4a",
                    "vcodec": "none",
                    "acodec": "mp4a",
                    "filesize": 5,
                    "abr": 128,
                },
            ]
        }
    )
    assert result[0].requires_merge and result[0].audio_format_id == "a"
