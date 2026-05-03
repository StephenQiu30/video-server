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
    assert response.formats[1].filesize == 12345
    assert "仅视频" in response.formats[1].label
