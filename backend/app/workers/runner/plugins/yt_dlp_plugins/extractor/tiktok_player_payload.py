from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

PLAYER_UNAVAILABLE = "TikTok video not available from the official player"
PLAYER_TEMPORARY = "TikTok official player API temporarily unavailable"
PLAYER_SCHEMA_CHANGED = "TikTok official player response structure changed"

_LINK_STATUS_MARKERS = (
    "invalid parameter",
    "item not found",
    "video not found",
    "item unavailable",
    "video unavailable",
    "item deleted",
    "video deleted",
)
_MISSING_RESULT_MARKERS = ("nil", "not_found", "invalid", "unavailable", "deleted")
_MISSING = object()


def player_info(payload: object, video_id: str, player_url: str) -> dict[str, Any]:
    item = _player_item(_player_payload(payload, video_id), video_id)
    info = _format_info(item, video_id, player_url) if item is not None else None
    if info is None:
        raise player_failure(PLAYER_UNAVAILABLE, video_id)
    return info


def player_failure(message: str, video_id: str) -> ExtractorError:
    return ExtractorError(message, video_id=video_id, expected=True)


def _player_payload(payload: object, video_id: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    status_code = payload.get("status_code", _MISSING)
    if isinstance(status_code, bool) or not isinstance(status_code, int):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    if status_code == 0:
        return payload
    items = payload.get("items")
    if items not in (None, []):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    status_message = payload.get("status_msg")
    normalized = status_message.casefold() if isinstance(status_message, str) else ""
    message = (
        PLAYER_UNAVAILABLE
        if any(marker in normalized for marker in _LINK_STATUS_MARKERS)
        else PLAYER_TEMPORARY
    )
    raise player_failure(message, video_id)


def _player_item(payload: Mapping[str, Any], video_id: str) -> Mapping[str, Any] | None:
    items = payload.get("items", _MISSING)
    if items is _MISSING:
        raise player_failure(_missing_item_result(payload, video_id), video_id)
    if items is None:
        return _resolved_missing_item(payload, video_id)
    if not isinstance(items, list):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    if not items:
        return _resolved_missing_item(payload, video_id)
    for item in items:
        if not isinstance(item, Mapping):
            raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
        if str(item.get("id_str") or item.get("id")) == video_id:
            return item
    raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)


def _resolved_missing_item(
    payload: Mapping[str, Any], video_id: str
) -> Mapping[str, Any] | None:
    if "results" not in payload:
        return None
    message = _missing_item_result(payload, video_id)
    if message == PLAYER_UNAVAILABLE:
        return None
    raise player_failure(message, video_id)


def _missing_item_result(payload: Mapping[str, Any], video_id: str) -> str:
    results = payload.get("results")
    if not isinstance(results, list):
        return PLAYER_SCHEMA_CHANGED
    for result in results:
        if not isinstance(result, Mapping):
            return PLAYER_SCHEMA_CHANGED
        if str(result.get("id_str") or result.get("id")) != video_id:
            continue
        code = result.get("code")
        if not isinstance(code, str):
            return PLAYER_SCHEMA_CHANGED
        normalized = code.casefold()
        if any(marker in normalized for marker in _MISSING_RESULT_MARKERS):
            return PLAYER_UNAVAILABLE
        return PLAYER_SCHEMA_CHANGED if normalized == "ok" else PLAYER_TEMPORARY
    return PLAYER_SCHEMA_CHANGED


def _format_info(
    item: Mapping[str, Any],
    video_id: str,
    player_url: str,
) -> dict[str, Any] | None:
    video = item.get("video_info", _MISSING)
    if video is _MISSING or video is None:
        return None
    if not isinstance(video, Mapping):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    meta = video.get("meta")
    if meta is not None and not isinstance(meta, Mapping):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    metadata = meta or {}
    profiles = video.get("profiles", _MISSING)
    if profiles is _MISSING or profiles is None:
        return None
    if not isinstance(profiles, list):
        raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
    formats: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, Mapping):
            raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
        address = profile.get("play_addr")
        if address is None:
            continue
        if not isinstance(address, Mapping):
            raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
        urls = address.get("url_list")
        if urls is None:
            continue
        if not isinstance(urls, list):
            raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
        _add_profile_formats(formats, seen_urls, profile, address, metadata, player_url)
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


def _add_profile_formats(
    formats: list[dict[str, Any]],
    seen_urls: set[str],
    profile: Mapping[str, Any],
    address: Mapping[str, Any],
    metadata: Mapping[str, Any],
    player_url: str,
) -> None:
    urls = address["url_list"]
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
                "format_id": f"player-{codec}-{height or 0}p-{bitrate or 0}-{index}",
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
                "http_headers": {"Referer": player_url},
            }
        )


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
