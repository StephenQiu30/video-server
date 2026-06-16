import pytest

from app.core.errors import AppError
from app.sources.models import (
    MediaVariant,
    SourceCapability,
    SourceContext,
    SourceInfo,
    SourceRequest,
    SubtitleTrack,
    source_info_to_parse_response,
)


class TestSourceRequest:
    def test_create_from_valid_url(self) -> None:
        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        assert req.hostname == "www.bilibili.com"
        assert req.normalized_url == "https://www.bilibili.com/video/BV1xx411c7mD"
        assert req.format_id is None

    def test_create_with_format_id(self) -> None:
        req = SourceRequest.from_url("https://example.com/v", format_id="best")
        assert req.format_id == "best"

    def test_rejects_empty_hostname(self) -> None:
        with pytest.raises(AppError) as exc_info:
            SourceRequest.from_url("not-a-url")
        assert exc_info.value.code == "invalid_url"


class TestSourceCapability:
    def test_enum_values(self) -> None:
        assert SourceCapability.HAS_VIDEO == "has_video"
        assert SourceCapability.HAS_AUDIO == "has_audio"
        assert SourceCapability.HAS_SUBTITLES == "has_subtitles"
        assert SourceCapability.MULTI_RESOLUTION == "multi_resolution"


class TestMediaVariant:
    def test_video_plus_audio_stream_type(self) -> None:
        v = MediaVariant(format_id="1", vcodec="h264", acodec="aac")
        assert v.stream_type == "video+audio"

    def test_video_only_stream_type(self) -> None:
        v = MediaVariant(format_id="1", vcodec="h264", acodec="none")
        assert v.stream_type == "video-only"

    def test_audio_only_stream_type(self) -> None:
        v = MediaVariant(format_id="1", vcodec="none", acodec="aac")
        assert v.stream_type == "audio-only"

    def test_none_codecs(self) -> None:
        v = MediaVariant(format_id="1")
        assert v.stream_type is None

    def test_frozen(self) -> None:
        v = MediaVariant(format_id="1")
        with pytest.raises(AttributeError):
            v.format_id = "2"


class TestSubtitleTrack:
    def test_create(self) -> None:
        s = SubtitleTrack(language="en", ext="vtt", url="https://example.com/sub.vtt")
        assert s.language == "en"
        assert s.ext == "vtt"


class TestSourceInfo:
    def test_create_with_variants(self) -> None:
        variants = [MediaVariant(format_id="1", vcodec="h264", acodec="aac")]
        info = SourceInfo(
            title="Test",
            variants=variants,
            capabilities={SourceCapability.HAS_VIDEO, SourceCapability.HAS_AUDIO},
            raw_info={"title": "Test"},
        )
        assert info.title == "Test"
        assert len(info.variants) == 1
        assert SourceCapability.HAS_VIDEO in info.capabilities

    def test_empty_variants(self) -> None:
        info = SourceInfo(variants=[], capabilities=set(), raw_info={})
        assert info.title is None
        assert len(info.variants) == 0


class TestSourceContext:
    def test_create_with_profile(self) -> None:
        from app.services.platforms import find_platform_profile

        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        profile = find_platform_profile(req.url)
        ctx = SourceContext(request=req, platform_profile=profile, adapter_name="bilibili")
        assert ctx.platform_profile is not None
        assert ctx.platform_profile.id == "bilibili"

    def test_create_without_profile(self) -> None:
        req = SourceRequest.from_url("https://unknown-site.com/video")
        ctx = SourceContext(request=req, platform_profile=None, adapter_name="ytdlp-fallback")
        assert ctx.platform_profile is None


class TestSourceInfoToParseResponse:
    def test_basic_conversion(self) -> None:
        from app.services.platforms import find_platform_profile

        variants = [
            MediaVariant(
                format_id="30080",
                ext="mp4",
                height=1080,
                width=1920,
                vcodec="h264",
                acodec="none",
            ),
        ]
        info = SourceInfo(
            title="Bilibili sample",
            cover_url="https://example.com/cover.jpg",
            duration_seconds=580,
            extractor="BiliBili",
            variants=variants,
            subtitles=[],
            capabilities={SourceCapability.HAS_VIDEO},
            raw_info={},
        )
        profile = find_platform_profile("https://www.bilibili.com/video/BV1xx411c7mD")
        resp = source_info_to_parse_response(
            url="https://www.bilibili.com/video/BV1xx411c7mD",
            info=info,
            platform_profile=profile,
        )
        assert resp.title == "Bilibili sample"
        assert resp.source_site == "B 站"
        assert resp.platform_id == "bilibili"
        assert resp.duration_seconds == 580
        assert resp.extractor == "BiliBili"

    def test_resolution_presets_from_variants(self) -> None:
        variants = [
            MediaVariant(format_id="v1", height=1080, width=1920, vcodec="h264", acodec="aac"),
            MediaVariant(format_id="audio", vcodec="none", acodec="aac"),
        ]
        info = SourceInfo(
            title="HD",
            variants=variants,
            subtitles=[],
            capabilities={SourceCapability.HAS_VIDEO, SourceCapability.HAS_AUDIO},
            raw_info={},
        )
        resp = source_info_to_parse_response(
            url="https://example.com/v",
            info=info,
            platform_profile=None,
        )
        presets = [f for f in resp.formats if f.kind != "raw"]
        assert len(presets) >= 5
        quality_labels = [p.quality_label for p in presets]
        assert "推荐" in quality_labels
        assert "最高 1080p" in quality_labels

    def test_empty_variants_gets_recommended_fallback(self) -> None:
        info = SourceInfo(variants=[], subtitles=[], capabilities=set(), raw_info={})
        resp = source_info_to_parse_response(
            url="https://example.com/v",
            info=info,
            platform_profile=None,
        )
        assert len(resp.formats) >= 1
        assert resp.formats[0].kind == "recommended"
