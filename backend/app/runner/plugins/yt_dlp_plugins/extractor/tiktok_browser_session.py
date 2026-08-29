from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import urlsplit

from yt_dlp.extractor.tiktok import TikTokIE  # type: ignore[import-untyped]
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_PLAYER_API = "https://www.tiktok.com/player/api/v1/items"
_PLAYER_URL = "https://www.tiktok.com/player/v1/{video_id}"
_BROWSER_HEADERS = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}


class _TikTokBrowserSessionIE(TikTokIE, plugin_name="browser_session"):  # type: ignore[misc, call-arg]
    """Resolve public video metadata through TikTok's first-party player API.

    The canonical webpage is guarded by a probabilistic JavaScript challenge,
    while TikTok's own embeddable player uses a stable item endpoint. Prefer
    that endpoint and retain the upstream webpage extractor only as a fallback.
    """

    def _real_extract(self, url: str) -> dict[str, Any]:
        video_id, _ = self._match_valid_url(url).group("id", "user_id")
        player_url = _PLAYER_URL.format(video_id=video_id)
        payload = self._download_json(
            _PLAYER_API,
            video_id,
            note="Downloading TikTok player metadata",
            fatal=False,
            query={"item_ids": video_id},
            headers={**_BROWSER_HEADERS, "Referer": player_url},
        )
        if isinstance(payload, Mapping):
            item = _player_item(payload, video_id)
            if item is not None:
                info = _player_info(item, video_id, player_url)
                if info is not None:
                    return info
            if payload.get("status_code") == 0:
                raise ExtractorError(
                    "TikTok video not available from the official player",
                    video_id=video_id,
                    expected=True,
                )
        return cast(dict[str, Any], super()._real_extract(url))

    def _download_webpage_handle(
        self,
        url_or_request: Any,
        video_id: str | None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        kwargs = _without_transport_impersonation(kwargs)
        return super()._download_webpage_handle(
            url_or_request,
            video_id,
            *args,
            **kwargs,
        )


def _without_transport_impersonation(options: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(options)
    normalized.pop("impersonate", None)
    return normalized


def _player_item(payload: Mapping[str, Any], video_id: str) -> Mapping[str, Any] | None:
    items = payload.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, Mapping):
            continue
        if str(item.get("id_str") or item.get("id")) == video_id:
            return item
    return None


def _player_info(
    item: Mapping[str, Any],
    video_id: str,
    player_url: str,
) -> dict[str, Any] | None:
    video = item.get("video_info")
    if not isinstance(video, Mapping):
        return None
    meta = video.get("meta")
    metadata = meta if isinstance(meta, Mapping) else {}
    profiles = video.get("profiles")
    if not isinstance(profiles, list):
        return None
    formats: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, Mapping):
            continue
        address = profile.get("play_addr")
        if not isinstance(address, Mapping):
            continue
        urls = address.get("url_list")
        if not isinstance(urls, list):
            continue
        bitrate = _positive_int(profile.get("bitrate"))
        codec = str(profile.get("codec_type") or "h264").casefold()
        height = _positive_int(address.get("height") or metadata.get("height"))
        width = _positive_int(address.get("width") or metadata.get("width"))
        fps = _positive_int(profile.get("fps")) or 30
        for index, media_url in enumerate(urls):
            if not _https_url(media_url) or media_url in seen_urls:
                continue
            seen_urls.add(media_url)
            formats.append(
                {
                    "format_id": (
                        f"player-{codec}-{height or 0}p-{bitrate or 0}-{index}"
                    ),
                    "url": media_url,
                    "ext": "mp4",
                    "protocol": "https",
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "tbr": bitrate / 1000 if bitrate is not None else None,
                    "filesize": _positive_int(address.get("data_size")),
                    "vcodec": codec,
                    "acodec": "aac",
                    "http_headers": {**_BROWSER_HEADERS, "Referer": player_url},
                }
            )
    if not formats:
        return None
    author = item.get("author_info")
    author_info = author if isinstance(author, Mapping) else {}
    duration_ms = _positive_int(metadata.get("duration"))
    return {
        "id": video_id,
        "title": str(item.get("desc") or f"TikTok video {video_id}"),
        "duration": duration_ms / 1000 if duration_ms is not None else None,
        "thumbnail": _first_https_url(video.get("cover")),
        "uploader": author_info.get("nickname"),
        "uploader_id": author_info.get("unique_id"),
        "availability": "public",
        "formats": formats,
        "webpage_url": player_url,
        "live_status": "not_live",
    }


def _first_https_url(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    urls = value.get("url_list")
    if not isinstance(urls, list):
        return None
    return next((url for url in urls if _https_url(url)), None)


def _https_url(value: object) -> bool:
    return isinstance(value, str) and urlsplit(value).scheme == "https"


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
