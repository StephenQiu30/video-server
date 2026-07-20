from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.api.dependencies import get_db_session
from src.core.logging import RedactedJsonFormatter, _safe_value, configure_logging
from src.downloads.schemas import DownloadJob as DownloadJobSchema
from src.media.download import content_type_for
from src.media.schemas import InspectedMedia, MediaFormat
from src.media.sha256 import sha256_file
from src.media.url_policy import (
    URLPolicy,
    UrlPolicyError,
    assert_safe_url,
    validate_url,
)
from src.media.yt_dlp import MediaInspectTimeout, UnsupportedMediaError, YtdlpExtractor


def test_media_helper_edges(tmp_path: Path) -> None:
    path = tmp_path / "video.bin"
    path.write_bytes(b"video")
    with pytest.raises(ValueError, match="chunk_size"):
        sha256_file(path, chunk_size=0)
    assert content_type_for(".webm") == "video/webm"
    assert content_type_for(".unknown") == "application/octet-stream"
    assert assert_safe_url("https://example.test/video", resolve=False).endswith(
        "/video"
    )


def test_url_policy_rejects_parser_and_resolver_edges() -> None:
    invalid = (
        "",
        "ftp://example.test/video",
        "https://user:pass@example.test/video",
        "https://example.test:8443/video",
        "https://example.test/video#fragment",
        "https://example.test/video with-space",
        "https://[bad",
    )
    for value in invalid:
        with pytest.raises(UrlPolicyError):
            validate_url(value, resolve=False)
    with pytest.raises(UrlPolicyError, match="invalid address"):
        URLPolicy(resolver=lambda *_: ["not-an-ip"]).validate(
            "https://example.test/video"
        )
    with pytest.raises(UrlPolicyError, match="could not be resolved"):
        URLPolicy(resolver=lambda *_: []).validate("https://example.test/video")
    with pytest.raises(UrlPolicyError, match="non-public"):
        URLPolicy(resolver=lambda *_: ["127.0.0.1"]).validate(
            "https://example.test/video"
        )
    assert (
        URLPolicy(resolver=lambda *_: ["8.8.8.8"])
        .check_redirect("https://example.test/redirect")
        .endswith("/redirect")
    )


def test_ytdlp_normalization_and_async_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class Client:
        def __init__(self, _: dict[str, object]) -> None:
            pass

        def __enter__(self) -> Client:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def extract_info(self, *_: object, **__: object) -> object:
            return {
                "extractor": "Example",
                "id": 10,
                "title": None,
                "duration": 0,
                "formats": [
                    {
                        "format_id": "v",
                        "height": 360,
                        "width": 640,
                        "ext": "mp4",
                        "vcodec": "avc1",
                        "acodec": "mp4a",
                    }
                ],
            }

    extractor = YtdlpExtractor(
        ytdlp_class=Client,
        allowed_extractors=("example",),
        policy=URLPolicy(resolver=lambda *_: ["8.8.8.8"]),
    )
    result = extractor.inspect("https://example.test/video")
    assert result.extractor_key == "Example" and result.duration_seconds is None
    with pytest.raises(UnsupportedMediaError):
        extractor._normalize(
            "https://example.test/video",
            {"extractor_key": "Other", "formats": []},
        )

    async def timeout_inspect(_: str) -> object:
        await asyncio.sleep(0.02)
        return result

    monkeypatch.setattr(extractor, "inspect", timeout_inspect)
    extractor.timeout_seconds = 0
    with pytest.raises(MediaInspectTimeout):
        asyncio.run(extractor.inspect_async("https://example.test/video"))


def test_media_schemas_accept_mapping_decimal_and_naive_dates() -> None:
    format_id = uuid.uuid4()
    media_id = uuid.uuid4()
    expires = datetime(2026, 1, 1)
    fmt = MediaFormat.from_model(
        {
            "id": format_id,
            "label": "720p",
            "width": 1280,
            "height": 720,
            "fps": Decimal("29.97"),
            "container": "mp4",
            "video_codec": "avc1",
            "audio_codec": "mp4a",
            "estimated_size_bytes": None,
            "requires_merge": False,
        }
    )
    media = InspectedMedia.from_model(
        {
            "id": media_id,
            "title": "Video",
            "extractor_key": "Example",
            "expires_at": expires,
            "formats": [fmt],
        }
    )
    assert media.platform == "Example" and media.formats[0].fps == 29.97
    assert media.model_dump(mode="json")["expires_at"].endswith("Z")


def test_logging_redacts_nested_values_and_exception() -> None:
    assert (
        _safe_value("payload", {"url": "https://example.test/x?token=secret"})["url"]
        == "https://example.test/x"
    )
    record = logging.LogRecord(
        "video",
        logging.ERROR,
        __file__,
        1,
        "failed",
        (),
        (ValueError, ValueError("secret"), None),
    )
    record.session_secret = "secret"
    payload = json.loads(RedactedJsonFormatter().format(record))
    assert payload["session_secret"] == "***"
    assert payload["exception_type"] == "ValueError"
    root = logging.getLogger()
    original = list(root.handlers)
    try:
        root.handlers.clear()
        configure_logging("warning")
        configure_logging("error")
        assert root.level == logging.ERROR and len(root.handlers) == 1
    finally:
        root.handlers[:] = original


@pytest.mark.asyncio
async def test_db_session_rolls_back_generator_failures() -> None:
    class Session:
        def __init__(self) -> None:
            self.rollbacks = 0

        async def __aenter__(self) -> Session:
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def rollback(self) -> None:
            self.rollbacks += 1

    session = Session()

    class Factory:
        def __call__(self) -> Session:
            return session

    import src.api.dependencies as dependencies

    original = dependencies.get_session_factory
    dependencies.get_session_factory = lambda: Factory()  # type: ignore[assignment]
    try:
        generator = get_db_session()
        await generator.__anext__()
        with pytest.raises(RuntimeError):
            await generator.athrow(RuntimeError("boom"))
        assert session.rollbacks == 1
    finally:
        dependencies.get_session_factory = original


def test_download_schema_error_and_datetime_mapping() -> None:
    now = datetime.now(UTC)
    value = SimpleNamespace(
        id=uuid.uuid4(),
        status="failed",
        stage=None,
        progress_percent=None,
        downloaded_bytes=None,
        total_bytes=None,
        error_code="failed",
        error_message="bad",
        artifact=None,
        created_at=now,
        updated_at=now,
    )
    result = DownloadJobSchema.from_model(value)
    assert result.error is not None and result.error.code == "failed"
    assert result.model_dump(mode="json")["created_at"].endswith("Z")
