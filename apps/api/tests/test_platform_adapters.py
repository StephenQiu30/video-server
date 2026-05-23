import pytest

from app.core.errors import AppError
from app.services import download_adapter
from app.services.download_adapter import AdapterRegistry, BilibiliAdapter, DomesticShortVideoAdapter, DownloadEngineAdapter


def test_bilibili_adapter_is_selected_for_bilibili_host(monkeypatch) -> None:
    captured = {}

    def fake_extract(url: str) -> dict:
        captured["url"] = url
        return {
            "title": "Bilibili sample",
            "duration": 12,
            "extractor_key": "BiliBili",
            "formats": [
                {
                    "format_id": "30080",
                    "width": 1920,
                    "height": 1080,
                    "ext": "mp4",
                    "acodec": "none",
                    "vcodec": "h264",
                }
            ],
        }

    monkeypatch.setattr(download_adapter, "_extract_with_ytdlp", fake_extract)
    adapter = DownloadEngineAdapter()

    result = adapter.parse("https://www.bilibili.com/video/BV1xx411c7mD")

    assert result.source_site == "B 站"
    assert captured["url"] == "https://www.bilibili.com/video/BV1xx411c7mD"


def test_domestic_short_video_adapter_is_selected_for_douyin_host(monkeypatch) -> None:
    def fake_extract(url: str) -> dict:
        return {
            "title": "Douyin sample",
            "duration": 8,
            "extractor_key": "Douyin",
            "formats": [
                {
                    "format_id": "audio",
                    "ext": "m4a",
                    "vcodec": "none",
                }
            ],
        }

    monkeypatch.setattr(download_adapter, "_extract_with_ytdlp", fake_extract)
    adapter = DownloadEngineAdapter(AdapterRegistry(adapters=[DomesticShortVideoAdapter(), BilibiliAdapter()]))

    result = adapter.parse("https://v.douyin.com/iJxxqxx/")

    assert result.source_site == "抖音"
    assert result.duration_seconds == 8


def test_parse_restricted_content_maps_to_platform_restricted_code() -> None:
    class RestrictionAdapter(BilibiliAdapter):
        def parse(self, url: str):
            raise RuntimeError("need to login with this account")

    with pytest.raises(AppError) as exc_info:
        DownloadEngineAdapter(AdapterRegistry(adapters=[RestrictionAdapter()])).parse(
            "https://www.bilibili.com/video/BV1xx411c7mD"
        )

    assert exc_info.value.code == "platform_restricted"

