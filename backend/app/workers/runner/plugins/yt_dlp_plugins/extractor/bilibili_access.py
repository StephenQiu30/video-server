"""Guard paid Bilibili metadata before upstream turns preview streams into formats."""

from __future__ import annotations

from typing import Any

from yt_dlp.extractor.bilibili import BiliBiliIE  # type: ignore[import-untyped]

from ._content_access import (
    enforce_bilibili_access,
    enforce_bilibili_playinfo,
)


class _BiliBiliAccessIE(BiliBiliIE, plugin_name="content_access"):  # type: ignore[misc, call-arg]
    def _search_json(
        self,
        start_pattern: str,
        string: str,
        name: str,
        video_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        result = super()._search_json(
            start_pattern, string, name, video_id, *args, **kwargs
        )
        if name == "initial state" and isinstance(result, dict):
            for key in ("videoData", "videoInfo"):
                video = result.get(key)
                if isinstance(video, dict):
                    enforce_bilibili_access(video)
        if name == "play info" and isinstance(result, dict):
            data = result.get("data")
            if isinstance(data, dict):
                enforce_bilibili_playinfo(data)
        return result

    def extract_formats(self, play_info: Any) -> Any:
        if isinstance(play_info, dict):
            enforce_bilibili_playinfo(play_info)
        return super().extract_formats(play_info)
