import pytest
from pydantic import ValidationError

from app.schemas import TaskCreate
from app.services.download_adapter import (
    DownloadEngineAdapter,
    RECOMMENDED_FORMAT_ID,
    WATERMARK_HINT_TEXT,
    _safe_int,
)


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
    assert response.formats[2].available is True
    assert "降级" in (response.formats[2].note or "")
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
    # Source is 360p: 1080/720/480 unavailable, 360 available
    assert presets[1].available is False
    assert presets[2].available is False
    assert presets[3].available is False
    assert presets[4].available is True
    assert presets[-1].format_id == "bv*[height<=360]+ba/b[height<=360]"


def test_resolution_presets_available_when_source_has_matching_height() -> None:
    """Source with 1080p: all presets at or below 1080p are available."""
    response = DownloadEngineAdapter()._to_response(
        "https://example.com/video",
        {
            "title": "HD source",
            "extractor_key": "Generic",
            "formats": [
                {
                    "format_id": "best",
                    "height": 1080,
                    "width": 1920,
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                },
            ],
        },
    )
    presets = [f for f in response.formats if f.kind != "raw"]
    assert len(presets) == 5
    labels = [p.quality_label for p in presets]
    assert labels == ["推荐", "最高 1080p", "最高 720p", "最高 480p", "最高 360p"]

    # All presets have required fields
    for p in presets:
        assert p.quality_label is not None
        assert isinstance(p.available, bool)
        assert p.note is not None

    # Recommended is always available
    assert presets[0].available is True
    # 1080p exact match → available, no degradation
    assert presets[1].available is True
    assert "降级" not in (presets[1].note or "")
    # 720p/480p/360p have source above → degraded but available
    for p in presets[2:]:
        assert p.available is True
        assert "降级" in (p.note or "")


def test_resolution_presets_degraded_when_source_below_target() -> None:
    """Source with 720p: 1080p unavailable, 720p available, lower tiers degraded."""
    response = DownloadEngineAdapter()._to_response(
        "https://example.com/video",
        {
            "title": "720p source",
            "extractor_key": "Generic",
            "formats": [
                {
                    "format_id": "mid",
                    "height": 720,
                    "width": 1280,
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                },
            ],
        },
    )
    presets = [f for f in response.formats if f.kind != "raw"]

    # 1080p: no source at or above → unavailable
    assert presets[1].quality_label == "最高 1080p"
    assert presets[1].available is False
    assert "未提供" in (presets[1].note or "")

    # 720p: exact match → available, no degradation
    assert presets[2].quality_label == "最高 720p"
    assert presets[2].available is True
    assert "降级" not in (presets[2].note or "")

    # 480p/360p: source above → degraded but available
    for p in presets[3:]:
        assert p.available is True
        assert "降级" in (p.note or "")


def test_resolution_presets_unavailable_when_no_source_at_or_above() -> None:
    """Source with only 360p: 1080/720/480 unavailable, 360 available."""
    response = DownloadEngineAdapter()._to_response(
        "https://example.com/video",
        {
            "title": "Low quality source",
            "extractor_key": "Generic",
            "formats": [
                {
                    "format_id": "low",
                    "height": 360,
                    "width": 640,
                    "ext": "mp4",
                    "vcodec": "h264",
                    "acodec": "aac",
                },
            ],
        },
    )
    presets = [f for f in response.formats if f.kind != "raw"]

    # Recommended always available
    assert presets[0].available is True

    # 1080p, 720p, 480p: no source at or above → unavailable
    for p in presets[1:4]:
        assert p.available is False
        assert "未提供" in (p.note or "")

    # 360p: exact match → available
    assert presets[4].quality_label == "最高 360p"
    assert presets[4].available is True


def test_task_create_rejects_too_long_format_selector() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(url="https://example.com/video", format_id="x" * 101)


def test_watermark_hint_set_for_douyin_formats() -> None:
    """Douyin is a known watermark platform; all formats should carry the hint."""
    response = DownloadEngineAdapter()._to_response(
        "https://www.douyin.com/video/456",
        {
            "title": "Douyin watermark test",
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
            ],
        },
    )

    assert response.source_site == "抖音"
    for fmt in response.formats:
        assert fmt.watermark_hint == WATERMARK_HINT_TEXT, (
            f"Format {fmt.format_id} (kind={fmt.kind}) missing watermark_hint for Douyin"
        )


def test_watermark_hint_absent_for_bilibili_formats() -> None:
    """Bilibili is not a known watermark platform; hint should be None."""
    response = DownloadEngineAdapter()._to_response(
        "https://www.bilibili.com/video/BV1iCR7BEEvo/",
        {
            "title": "Bilibili no-watermark test",
            "extractor_key": "BiliBili",
            "formats": [
                {
                    "format_id": "30080",
                    "width": 1920,
                    "height": 1080,
                    "ext": "mp4",
                    "filesize_approx": 50000,
                    "acodec": "none",
                }
            ],
        },
    )

    assert response.source_site == "B 站"
    for fmt in response.formats:
        assert fmt.watermark_hint is None, (
            f"Format {fmt.format_id} (kind={fmt.kind}) has unexpected watermark_hint for Bilibili"
        )


def test_watermark_hint_absent_for_unknown_platform() -> None:
    """Unknown platforms should not get a watermark hint."""
    response = DownloadEngineAdapter()._to_response(
        "https://unknown.example.com/video/789",
        {
            "title": "Unknown platform",
            "formats": [
                {
                    "format_id": "default",
                    "height": 720,
                    "ext": "mp4",
                    "vcodec": "h264",
                },
            ],
        },
    )

    for fmt in response.formats:
        assert fmt.watermark_hint is None
