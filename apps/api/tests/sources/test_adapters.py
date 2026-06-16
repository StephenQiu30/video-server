import pytest

from app.core.errors import AppError, ErrorCode
from app.sources.adapters.bilibili import BilibiliAdapter
from app.sources.adapters.domestic_short_video import DomesticShortVideoAdapter
from app.sources.adapters.ytdlp import YtDlpAdapter
from app.sources.models import SourceRequest


class TestYtDlpAdapter:
    def test_supports_any_url(self) -> None:
        adapter = YtDlpAdapter()
        req = SourceRequest.from_url("https://any-site.com/video")
        assert adapter.supports(req) is True

    def test_name(self) -> None:
        assert YtDlpAdapter().name == "ytdlp-fallback"

    def test_parse_calls_ytdlp(self, monkeypatch) -> None:
        from app.sources.adapters import ytdlp as ytdlp_mod

        def fake_extract(url: str) -> dict:
            return {
                "title": "Test",
                "duration": 10,
                "extractor_key": "Generic",
                "formats": [{"format_id": "1", "height": 720, "width": 1280, "ext": "mp4", "vcodec": "h264", "acodec": "aac"}],
            }

        monkeypatch.setattr(ytdlp_mod, "_extract_with_ytdlp", fake_extract)
        adapter = YtDlpAdapter()
        req = SourceRequest.from_url("https://example.com/v")
        info = adapter.parse(req)
        assert info.title == "Test"
        assert len(info.variants) == 1

    def test_map_error_restricted(self) -> None:
        adapter = YtDlpAdapter()
        err = adapter.map_error(RuntimeError("need to login"))
        assert err.code == "platform_restricted"

    def test_map_error_rate_limit(self) -> None:
        adapter = YtDlpAdapter()
        err = adapter.map_error(RuntimeError("429 too many requests"))
        assert err.code == "platform_rate_limited"

    def test_map_error_unsupported(self) -> None:
        adapter = YtDlpAdapter()
        err = adapter.map_error(RuntimeError("unsupported url"))
        assert err.code == "unsupported_platform"

    def test_map_error_timeout(self) -> None:
        adapter = YtDlpAdapter()
        err = adapter.map_error(RuntimeError("connection timed out"))
        assert err.code == "platform_unavailable"

    def test_map_error_default(self) -> None:
        adapter = YtDlpAdapter()
        err = adapter.map_error(RuntimeError("something weird"))
        assert err.code == "parse_failed"


class TestBilibiliAdapter:
    def test_supports_bilibili_url(self) -> None:
        adapter = BilibiliAdapter()
        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        assert adapter.supports(req) is True

    def test_rejects_non_bilibili_url(self) -> None:
        adapter = BilibiliAdapter()
        req = SourceRequest.from_url("https://www.youtube.com/watch?v=abc")
        assert adapter.supports(req) is False

    def test_name(self) -> None:
        assert BilibiliAdapter().name == "bilibili"

    def test_map_error_uses_platform_name(self) -> None:
        adapter = BilibiliAdapter()
        err = adapter.map_error(RuntimeError("need to login"))
        assert err.code == "platform_restricted"
        assert "B 站" in err.message


class TestDomesticShortVideoAdapter:
    def test_supports_douyin(self) -> None:
        adapter = DomesticShortVideoAdapter()
        req = SourceRequest.from_url("https://v.douyin.com/iJxxqxx/")
        assert adapter.supports(req) is True

    def test_supports_kuaishou(self) -> None:
        adapter = DomesticShortVideoAdapter()
        req = SourceRequest.from_url("https://www.kuaishou.com/short-video/abc")
        assert adapter.supports(req) is True

    def test_supports_xiaohongshu(self) -> None:
        adapter = DomesticShortVideoAdapter()
        req = SourceRequest.from_url("https://www.xiaohongshu.com/explore/abc")
        assert adapter.supports(req) is True

    def test_rejects_bilibili(self) -> None:
        adapter = DomesticShortVideoAdapter()
        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        assert adapter.supports(req) is False

    def test_name(self) -> None:
        assert DomesticShortVideoAdapter().name == "short-video"
