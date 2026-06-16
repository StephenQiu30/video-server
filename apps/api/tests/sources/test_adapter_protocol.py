import pytest

from app.core.errors import AppError, ErrorCode
from app.sources.adapter import VideoSourceAdapter
from app.sources.models import SourceInfo, SourceRequest


class TestVideoSourceAdapterProtocol:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            VideoSourceAdapter()  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        class DummyAdapter(VideoSourceAdapter):
            @property
            def name(self) -> str:
                return "dummy"

            def supports(self, request: SourceRequest) -> bool:
                return True

            def parse(self, request: SourceRequest) -> SourceInfo:
                return SourceInfo(variants=[], capabilities=set(), raw_info={})

            def map_error(self, exc: Exception) -> AppError:
                return AppError(ErrorCode.PARSE_FAILED, "test", 422)

        adapter = DummyAdapter()
        assert adapter.name == "dummy"
        req = SourceRequest.from_url("https://example.com/v")
        assert adapter.supports(req) is True
        info = adapter.parse(req)
        assert isinstance(info, SourceInfo)

    def test_missing_parse_raises(self) -> None:
        class IncompleteAdapter(VideoSourceAdapter):
            @property
            def name(self) -> str:
                return "incomplete"

            def supports(self, request: SourceRequest) -> bool:
                return True

            def map_error(self, exc: Exception) -> AppError:
                return AppError(ErrorCode.PARSE_FAILED, "test", 422)

        with pytest.raises(TypeError):
            IncompleteAdapter()  # type: ignore[abstract]
