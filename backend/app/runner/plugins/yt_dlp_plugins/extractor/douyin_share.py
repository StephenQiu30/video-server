from __future__ import annotations

from typing import Any, cast

from yt_dlp.extractor.tiktok import DouyinIE  # type: ignore[import-untyped]
from yt_dlp.utils import int_or_none  # type: ignore[import-untyped]

_SHARE_PAGE = "https://www.iesdouyin.com/share/video/{video_id}/"
_MOBILE_HEADERS = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    ),
}


def _correct_download_addr_dimensions(
    info: dict[str, Any], aweme_detail: dict[str, Any]
) -> dict[str, Any]:
    """Align Douyin's download address metadata with the source video dimensions."""

    video = aweme_detail.get("video")
    if not isinstance(video, dict):
        return info
    source_width = int_or_none(video.get("width"))
    source_height = int_or_none(video.get("height"))
    if (
        source_width is None
        or source_height is None
        or source_width <= 0
        or source_height <= 0
        or source_width <= source_height
    ):
        # Upstream already maps Douyin's short-edge resolution correctly for
        # portrait videos. Its width/height assignment is only reversed for
        # landscape download_addr variants.
        return info
    formats = info.get("formats")
    if not isinstance(formats, list):
        return info
    for media_format in formats:
        if not isinstance(media_format, dict):
            continue
        format_id = media_format.get("format_id")
        if isinstance(format_id, str) and format_id.startswith("download_addr"):
            short_edge = int_or_none(media_format.get("width"))
            if short_edge is None or short_edge <= 0:
                continue
            media_format["width"] = round(short_edge * source_width / source_height)
            media_format["height"] = short_edge
    return info


class _DouyinSharePageIE(DouyinIE, plugin_name="share_page"):  # type: ignore[misc, call-arg]
    """Prefer Douyin's public share-page data when the web API needs cookies."""

    def _parse_aweme_video_app(self, aweme_detail: dict[str, Any]) -> dict[str, Any]:
        """Correct download_addr dimensions that Douyin currently under-reports."""

        return _correct_download_addr_dimensions(
            cast(dict[str, Any], super()._parse_aweme_video_app(aweme_detail)),
            aweme_detail,
        )

    def _real_extract(self, url: str) -> dict[str, Any]:
        video_id = self._match_id(url)
        webpage = self._download_webpage(
            _SHARE_PAGE.format(video_id=video_id),
            video_id,
            note="Downloading Douyin public share page",
            fatal=False,
            headers=_MOBILE_HEADERS,
        )
        if webpage:
            router_data = self._search_json(
                r"window\._ROUTER_DATA\s*=\s*",
                webpage,
                "Douyin router data",
                video_id,
                fatal=False,
            )
            item = _router_item(router_data, video_id)
            if item is not None:
                try:
                    info = self._parse_aweme_video_app(item)
                except (AttributeError, KeyError, TypeError, ValueError):
                    info = {}
                formats = info.get("formats")
                if isinstance(formats, list) and any(
                    isinstance(media_format, dict)
                    and isinstance(media_format.get("url"), str)
                    and bool(media_format["url"])
                    for media_format in formats
                ):
                    title = " ".join(str(info.get("title") or "").split())
                    info["title"] = title or video_id
                    return info

        return cast(dict[str, Any], super()._real_extract(url))


def _router_item(payload: object, expected_id: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    loader_data = payload.get("loaderData")
    if not isinstance(loader_data, dict):
        return None
    for node in loader_data.values():
        if not isinstance(node, dict):
            continue
        response = node.get("videoInfoRes")
        if not isinstance(response, dict):
            continue
        items = response.get("item_list")
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and str(item.get("aweme_id")) == expected_id:
                video = item.get("video")
                if not isinstance(video, dict):
                    continue
                normalized = dict(item)
                normalized_video = dict(video)
                if not isinstance(normalized_video.get("bit_rate"), list):
                    normalized_video["bit_rate"] = []
                normalized["video"] = normalized_video
                return normalized
    return None
