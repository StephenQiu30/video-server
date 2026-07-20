import pytest
from src.media.formats import FormatPolicyError, normalize_formats


def test_normalize_formats_deduplicates_height_and_prefers_av() -> None:
    result = normalize_formats(
        {
            "formats": [
                {
                    "format_id": "v1080",
                    "height": 1080,
                    "width": 1920,
                    "vcodec": "avc1",
                    "acodec": "none",
                    "ext": "mp4",
                    "filesize": 100,
                },
                {
                    "format_id": "av1080",
                    "height": 1080,
                    "width": 1920,
                    "vcodec": "avc1",
                    "acodec": "mp4a",
                    "ext": "mp4",
                    "filesize": 200,
                },
                {
                    "format_id": "v720",
                    "height": 720,
                    "width": 1280,
                    "vcodec": "vp9",
                    "acodec": "none",
                    "ext": "webm",
                    "filesize": 80,
                },
                {
                    "format_id": "a128",
                    "acodec": "opus",
                    "vcodec": "none",
                    "abr": 128,
                    "ext": "webm",
                    "filesize": 12,
                },
            ]
        }
    )
    assert [item.label for item in result] == ["1080p", "720p"]
    assert result[0].requires_merge is False
    assert result[1].requires_merge is True
    assert result[1].selector == "v720+a128"
    assert [item.sort_order for item in result] == [0, 1]


def test_normalize_formats_skips_video_only_without_audio() -> None:
    with pytest.raises(FormatPolicyError):
        normalize_formats(
            {
                "formats": [
                    {
                        "format_id": "v720",
                        "height": 720,
                        "vcodec": "avc1",
                        "acodec": "none",
                        "ext": "mp4",
                    }
                ]
            }
        )
