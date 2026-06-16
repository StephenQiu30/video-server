import pytest

from app.core.errors import AppError, ErrorCode
from app.sources.adapter import VideoSourceAdapter
from app.sources.models import SourceInfo, SourceRequest
from app.sources.registry import SourceAdapterRegistry


class StubAdapter(VideoSourceAdapter):
    def __init__(self, adapter_name: str, match_hosts: set[str] | None = None) -> None:
        self._name = adapter_name
        self._match_hosts = match_hosts

    @property
    def name(self) -> str:
        return self._name

    def supports(self, request: SourceRequest) -> bool:
        if self._match_hosts is None:
            return True
        return request.hostname in self._match_hosts

    def parse(self, request: SourceRequest) -> SourceInfo:
        return SourceInfo(variants=[], capabilities=set(), raw_info={})

    def map_error(self, exc: Exception) -> AppError:
        return AppError(ErrorCode.PARSE_FAILED, "stub", 422)


class TestSourceAdapterRegistry:
    def test_register_and_get_adapter(self) -> None:
        registry = SourceAdapterRegistry(adapters=[])
        adapter = StubAdapter("bilibili", {"www.bilibili.com"})
        registry.register(adapter)

        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        assert registry.get_adapter(req).name == "bilibili"

    def test_register_first_takes_priority(self) -> None:
        registry = SourceAdapterRegistry(adapters=[StubAdapter("fallback")])
        registry.register_first(StubAdapter("priority", {"www.bilibili.com"}))

        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        assert registry.get_adapter(req).name == "priority"

    def test_first_matching_adapter_wins(self) -> None:
        a1 = StubAdapter("a1", {"www.bilibili.com"})
        a2 = StubAdapter("a2", {"www.bilibili.com"})
        registry = SourceAdapterRegistry(adapters=[a1, a2])

        req = SourceRequest.from_url("https://www.bilibili.com/video/BV1xx411c7mD")
        assert registry.get_adapter(req).name == "a1"

    def test_fallback_to_last_adapter(self) -> None:
        specific = StubAdapter("specific", {"www.bilibili.com"})
        fallback = StubAdapter("fallback")
        registry = SourceAdapterRegistry(adapters=[specific, fallback])

        req = SourceRequest.from_url("https://unknown-site.com/video")
        assert registry.get_adapter(req).name == "fallback"

    def test_default_initialization(self) -> None:
        registry = SourceAdapterRegistry()
        adapters = registry.list_adapters()
        assert len(adapters) == 3
        names = [a.name for a in adapters]
        assert "ytdlp-fallback" in names

    def test_list_adapters(self) -> None:
        registry = SourceAdapterRegistry(adapters=[StubAdapter("a"), StubAdapter("b")])
        assert len(registry.list_adapters()) == 2
