from __future__ import annotations

from app.services.platforms import find_platform_profile
from app.sources.adapters.ytdlp import YtDlpAdapter
from app.sources.models import SourceRequest


class DomesticShortVideoAdapter(YtDlpAdapter):
    """Adapter for domestic short video platforms (Douyin, Kuaishou, etc.)."""

    _PLATFORM_IDS = {"douyin", "kuaishou", "xiaohongshu", "ixigua", "weibo"}

    @property
    def name(self) -> str:
        return "short-video"

    def supports(self, request: SourceRequest) -> bool:
        profile = find_platform_profile(request.url)
        return bool(profile and profile.id in self._PLATFORM_IDS)
