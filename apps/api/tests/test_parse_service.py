import pytest

from app.core.errors import AppError, ErrorCode
from app.sources.models import SourceInfo, SourceRequest
from app.services.parse_service import ParseService


class TestParseService:
    def test_parse_delegates_to_registry(self, monkeypatch) -> None:
        from app.sources import registry as reg_mod

        captured = {}

        class FakeAdapter:
            name = "fake"

            def supports(self, request):
                return True

            def parse(self, request):
                captured["url"] = request.url
                return SourceInfo(
                    title="Test Video",
                    variants=[],
                    capabilities=set(),
                    raw_info={"title": "Test Video"},
                )

            def map_error(self, exc):
                return AppError(ErrorCode.PARSE_FAILED, "fake", 422)

        # Patch the registry to return our fake adapter
        original_get = reg_mod.SourceAdapterRegistry.get_adapter

        def fake_get(self, req):
            return FakeAdapter()

        monkeypatch.setattr(reg_mod.SourceAdapterRegistry, "get_adapter", fake_get)

        service = ParseService()
        resp = service.parse("https://example.com/video")
        assert resp.url == "https://example.com/video"
        assert captured["url"] == "https://example.com/video"

    def test_parse_maps_adapter_error(self, monkeypatch) -> None:
        from app.sources import registry as reg_mod

        class FailingAdapter:
            name = "failing"

            def supports(self, request):
                return True

            def parse(self, request):
                raise RuntimeError("need to login")

            def map_error(self, exc):
                return AppError(ErrorCode.PLATFORM_RESTRICTED, "restricted", 403)

        monkeypatch.setattr(
            reg_mod.SourceAdapterRegistry,
            "get_adapter",
            lambda self, req: FailingAdapter(),
        )

        service = ParseService()
        with pytest.raises(AppError) as exc_info:
            service.parse("https://example.com/video")
        assert exc_info.value.code == "platform_restricted"

    def test_parse_passes_through_app_error(self, monkeypatch) -> None:
        from app.sources import registry as reg_mod

        class AppErrorAdapter:
            name = "app-error"

            def supports(self, request):
                return True

            def parse(self, request):
                raise AppError(ErrorCode.INVALID_URL, "bad url", 422)

            def map_error(self, exc):
                return AppError(ErrorCode.PARSE_FAILED, "should not reach", 422)

        monkeypatch.setattr(
            reg_mod.SourceAdapterRegistry,
            "get_adapter",
            lambda self, req: AppErrorAdapter(),
        )

        service = ParseService()
        with pytest.raises(AppError) as exc_info:
            service.parse("https://example.com/video")
        assert exc_info.value.code == "invalid_url"

    def test_parse_returns_compatible_response(self, monkeypatch) -> None:
        from app.sources import registry as reg_mod
        from app.sources.models import MediaVariant, SourceCapability

        class SuccessAdapter:
            name = "success"

            def supports(self, request):
                return True

            def parse(self, request):
                return SourceInfo(
                    title="Video",
                    cover_url="https://example.com/cover.jpg",
                    duration_seconds=120,
                    extractor="Generic",
                    variants=[
                        MediaVariant(
                            format_id="v1",
                            height=720,
                            width=1280,
                            ext="mp4",
                            vcodec="h264",
                            acodec="aac",
                        ),
                    ],
                    subtitles=[],
                    capabilities={SourceCapability.HAS_VIDEO, SourceCapability.HAS_AUDIO},
                    raw_info={},
                )

            def map_error(self, exc):
                return AppError(ErrorCode.PARSE_FAILED, "test", 422)

        monkeypatch.setattr(
            reg_mod.SourceAdapterRegistry,
            "get_adapter",
            lambda self, req: SuccessAdapter(),
        )

        service = ParseService()
        resp = service.parse("https://example.com/video")
        assert resp.title == "Video"
        assert resp.duration_seconds == 120
        assert resp.cover_url == "https://example.com/cover.jpg"
        assert len(resp.formats) > 0
