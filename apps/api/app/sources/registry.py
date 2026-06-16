from __future__ import annotations

from app.sources.adapter import VideoSourceAdapter
from app.sources.models import SourceRequest


class SourceAdapterRegistry:
    """Ordered registry of video source adapters with first-match selection."""

    def __init__(self, adapters: list[VideoSourceAdapter] | None = None) -> None:
        if adapters is not None:
            self._adapters = list(adapters)
        else:
            self._adapters = _default_adapters()

    def register(self, adapter: VideoSourceAdapter) -> None:
        """Append adapter to the end of the chain."""
        self._adapters.append(adapter)

    def register_first(self, adapter: VideoSourceAdapter) -> None:
        """Insert adapter at the beginning of the chain."""
        self._adapters.insert(0, adapter)

    def get_adapter(self, request: SourceRequest) -> VideoSourceAdapter:
        """Return the first adapter whose supports() returns True."""
        for adapter in self._adapters:
            if adapter.supports(request):
                return adapter
        # Fallback: return the last adapter in the chain.
        return self._adapters[-1]

    def list_adapters(self) -> list[VideoSourceAdapter]:
        """Return a copy of the registered adapters list."""
        return list(self._adapters)


def _default_adapters() -> list[VideoSourceAdapter]:
    from app.sources.adapters.bilibili import BilibiliAdapter
    from app.sources.adapters.domestic_short_video import DomesticShortVideoAdapter
    from app.sources.adapters.ytdlp import YtDlpAdapter

    return [
        DomesticShortVideoAdapter(),
        BilibiliAdapter(),
        YtDlpAdapter(),
    ]
