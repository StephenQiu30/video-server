import pytest
from pydantic import ValidationError

from app.schemas import TaskCreate
from app.services.download_adapter import DownloadEngineAdapter, RECOMMENDED_FORMAT_ID, _safe_int


def test_safe_int_accepts_bilibili_float_duration() -> None:
    assert _safe_int(580.405) == 580


def test_parse_response_converts_duration_and_filesize() -> None:
    response = DownloadEngineAdapter()._to_response(
        "https://www.bilibili.com/video/BV1iCR7BEEvo/",
        {
            "title": "Bilibili sample",
            "duration": 580.405,
            "thumbnail": "https://example.com/cover.jpg",
            "extractor_key": "BiliBili",
            "formats": [
                {
                    "format_id": "30080",
                    "width": 1920,
                    "height": 1080,
                    "ext": "mp4",
                    "filesize_approx": 12345.67,
                    "acodec": "none",
                }
            ],
        },
    )

    assert response.duration_seconds == 580
    assert response.formats[0].format_id == RECOMMENDED_FORMAT_ID
    assert response.formats[0].label.startswith("推荐下载")
    assert response.source_site == "B 站"
    assert response.extractor == "BiliBili"
    assert response.formats[1].quality_label == "最高 1080p"
    assert response.formats[1].available is True
    assert response.formats[2].quality_label == "最高 720p"
    assert response.formats[2].available is False
    raw_format = next(item for item in response.formats if item.kind == "raw")
    assert raw_format.filesize == 12345
    assert "仅视频" in raw_format.label


def test_parse_response_builds_resolution_presets_from_available_heights() -> None:
    response = DownloadEngineAdapter()._to_response(
        "https://www.douyin.com/video/123",
        {
            "title": "Douyin sample",
            "extractor_key": "Douyin",
            "formats": [
                {
                    "format_id": "v-low",
                    "height": 360,
                    "width": 640,
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                },
                {
                    "format_id": "audio",
                    "ext": "m4a",
                    "vcodec": "none",
                },
            ],
        },
    )

    presets = [item for item in response.formats if item.kind != "raw"]
    assert response.source_site == "抖音"
    assert [item.quality_label for item in presets] == ["推荐", "最高 1080p", "最高 720p", "最高 480p", "最高 360p"]
    assert all(len(item.format_id) <= 100 for item in presets)
    assert presets[1].available is True
    assert presets[-1].format_id == "bv*[height<=360]+ba/b[height<=360]"


def test_task_create_rejects_too_long_format_selector() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(url="https://example.com/video", format_id="x" * 101)


def test_video_format_schema_has_optional_watermark_hint() -> None:
    """VideoFormat schema must expose watermark_hint (optional str)."""
    from app.schemas import VideoFormat

    fmt = VideoFormat(format_id="test", label="test", watermark_hint="可能含平台水印")
    assert fmt.watermark_hint == "可能含平台水印"

    fmt_none = VideoFormat(format_id="test", label="test")
    assert fmt_none.watermark_hint is None


def test_raw_format_declares_stream_type() -> None:
    """Raw formats must classify stream type: video+audio, video-only, audio-only."""
    response = DownloadEngineAdapter()._to_response(
        "https://www.bilibili.com/video/BV1iCR7BEEvo/",
        {
            "title": "Bilibili sample",
            "duration": 580,
            "thumbnail": "https://example.com/cover.jpg",
            "extractor_key": "BiliBili",
            "formats": [
                {
                    "format_id": "30080",
                    "width": 1920,
                    "height": 1080,
                    "ext": "mp4",
                    "filesize_approx": 12345,
                    "acodec": "none",
                },
                {
                    "format_id": "audio",
                    "ext": "m4a",
                    "vcodec": "none",
                },
            ],
        },
    )

    raw_formats = [item for item in response.formats if item.kind == "raw"]
    assert len(raw_formats) == 2, "Should expose both video-only and audio-only raw formats"

    for raw in raw_formats:
        assert raw.type in ("video+audio", "video-only", "audio-only"), (
            f"Raw format must declare stream type, got {raw.type}"
        )
        if raw.type != "audio-only":
            assert raw.resolution is not None, "Video raw format must preserve resolution"

    video_only = next(f for f in raw_formats if f.type == "video-only")
    audio_only = next(f for f in raw_formats if f.type == "audio-only")
    assert "仅视频" in video_only.label
    assert "仅音频" in audio_only.label


def test_watermark_platforms_hint_in_format_note() -> None:
    """Known watermark platforms (抖音/快手) should hint watermark status on formats."""
    response = DownloadEngineAdapter()._to_response(
        "https://www.douyin.com/video/123",
        {
            "title": "Douyin sample",
            "extractor_key": "Douyin",
            "formats": [
                {
                    "format_id": "v-low",
                    "height": 360,
                    "width": 640,
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                    "filesize_approx": 5000,
                },
            ],
        },
    )

    assert response.watermark_hint is not None, "ParseResponse must include watermark_hint"
    assert isinstance(response.watermark_hint, str)
    assert len(response.watermark_hint) > 0

    raw_formats = [item for item in response.formats if item.kind == "raw"]
    for fmt in raw_formats:
        assert fmt.watermark_hint is not None, (
            "Raw format from watermark platform must include watermark_hint"
        )
        assert "水印" in fmt.watermark_hint, (
            f"Watermark hint should mention 水印, got: {fmt.watermark_hint}"
        )


def test_watermark_free_platform_hint() -> None:
    """Watermark-free platforms (Bilibili) should indicate priority source."""
    response = DownloadEngineAdapter()._to_response(
        "https://www.bilibili.com/video/BV1iCR7BEEvo/",
        {
            "title": "Bilibili sample",
            "extractor_key": "BiliBili",
            "formats": [
                {
                    "format_id": "30080",
                    "width": 1920,
                    "height": 1080,
                    "ext": "mp4",
                    "acodec": "none",
                },
            ],
        },
    )

    assert response.watermark_hint == "优先可用源"

    raw_formats = [item for item in response.formats if item.kind == "raw"]
    for fmt in raw_formats:
        assert fmt.watermark_hint is not None
        assert "水印" not in fmt.watermark_hint, (
            f"Watermark-free platform format should not mention 水印, got: {fmt.watermark_hint}"
        )
