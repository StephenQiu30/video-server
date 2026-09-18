from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from yt_dlp.extractor.common import InfoExtractor  # type: ignore[import-untyped]
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_MOBILE_PAGE = "https://v.m.chenzhongtech.com/fw/photo/{video_id}"
_MOBILE_HEADERS = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://v.kuaishou.com/",
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Mobile Safari/537.36"
    ),
}
_DETAIL_PATH = re.compile(r"/(?:short-video|fw/photo)/(?P<id>[A-Za-z0-9]+)")
_ALLOWED_SHARE_DOMAINS = (
    "kuaishou.com",
    "kuaishou.cn",
    "chenzhongtech.com",
    "gifshow.com",
)
_LINK_UNAVAILABLE = "Kuaishou public link unavailable"


class KuaishouPublicIE(InfoExtractor):  # type: ignore[misc]
    """Extract public Kuaishou videos from the first-party mobile share page."""

    IE_NAME = "kuaishou:public"
    _VALID_URL = r"""(?x)https?://(?:
        (?:www\.)?kuaishou\.(?:com|cn)/short-video/(?P<web_id>[A-Za-z0-9]+)
        |(?:[^/]+\.)?kuaishou\.(?:com|cn)/fw/photo/(?P<web_photo_id>[A-Za-z0-9]+)
        |(?:www\.)?kuaishou\.(?:com|cn)/f/(?P<pc_share>[A-Za-z0-9_-]+)
        |v\.kuaishou\.(?:com|cn)/(?P<app_share>[A-Za-z0-9_-]+)
        |(?:[^/]+\.)?(?:chenzhongtech\.com|gifshow\.com)/fw/photo/(?P<mobile_id>[A-Za-z0-9]+)
    )"""

    def _real_extract(self, url: str) -> dict[str, Any]:
        match = self._match_valid_url(url)
        known_id = next(
            (
                value
                for value in (
                    match.group("web_id"),
                    match.group("web_photo_id"),
                    match.group("mobile_id"),
                )
                if value
            ),
            None,
        )
        request_url = _MOBILE_PAGE.format(video_id=known_id) if known_id else url
        webpage, response = self._download_webpage_handle(
            request_url,
            known_id or "share",
            note="Downloading Kuaishou public share page",
            headers=_MOBILE_HEADERS,
        )
        final_url = str(getattr(response, "url", request_url))
        video_id = _detail_id(final_url)
        if video_id is None or not _allowed_share_url(final_url):
            raise ExtractorError(_LINK_UNAVAILABLE, expected=True)

        state = self._search_json(
            r"window\.INIT_STATE\s*=\s*",
            webpage,
            "Kuaishou initial state",
            video_id,
            fatal=False,
        )
        photo = _state_photo(state, video_id)
        if photo is None:
            raise ExtractorError(_LINK_UNAVAILABLE, expected=True)
        if photo.get("photoType") != "VIDEO":
            raise ExtractorError(
                "Kuaishou image posts are not supported by the video runner",
                expected=True,
            )

        formats = _video_formats(photo)
        if not formats:
            raise ExtractorError(_LINK_UNAVAILABLE, expected=True)
        caption = " ".join(str(photo.get("caption") or "").split())
        return {
            "id": video_id,
            "title": caption or video_id,
            "description": caption or None,
            "duration": _milliseconds(photo.get("duration")),
            "timestamp": _milliseconds(photo.get("timestamp")),
            "uploader": photo.get("userName"),
            "uploader_id": photo.get("userEid") or photo.get("userId"),
            "thumbnail": _first_url(photo.get("coverUrls")),
            "view_count": photo.get("viewCount"),
            "like_count": photo.get("likeCount"),
            "comment_count": photo.get("commentCount"),
            "formats": formats,
            "webpage_url": final_url,
        }


def _allowed_share_url(url: str) -> bool:
    hostname = (urlsplit(url).hostname or "").casefold()
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in _ALLOWED_SHARE_DOMAINS
    )


def _detail_id(url: str) -> str | None:
    match = _DETAIL_PATH.search(urlsplit(url).path)
    return match.group("id") if match is not None else None


def _state_photo(payload: object, expected_id: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        photo = value.get("photo")
        if not isinstance(photo, dict):
            continue
        share_info = parse_qs(str(photo.get("share_info") or ""))
        if share_info.get("photoId") == [expected_id]:
            return photo
    return None


def _video_formats(photo: dict[str, Any]) -> list[dict[str, Any]]:
    formats: list[dict[str, Any]] = []
    manifest = photo.get("manifest")
    adaptation_sets = (
        manifest.get("adaptationSet") if isinstance(manifest, dict) else []
    )
    if isinstance(adaptation_sets, list):
        for adaptation in adaptation_sets:
            representations = (
                adaptation.get("representation") if isinstance(adaptation, dict) else []
            )
            if not isinstance(representations, list):
                continue
            for representation in representations:
                media_format = _representation_format(representation)
                if media_format is not None:
                    formats.append(media_format)
    if formats:
        return formats
    source_url = _first_url(photo.get("mainMvUrls"))
    if source_url:
        formats.append(
            {
                "format_id": "h264-source",
                "url": source_url,
                "ext": "mp4",
                "vcodec": "h264",
                "acodec": "aac",
                "width": photo.get("width"),
                "height": photo.get("height"),
                "http_headers": _MOBILE_HEADERS,
            }
        )
    return formats


def _representation_format(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    media_url = value.get("url") or _first_url(value.get("backupUrl"))
    if not isinstance(media_url, str) or not media_url.startswith("https://"):
        return None
    codec = str(value.get("videoCodec") or "avc").casefold()
    codec_name = "hevc" if codec in {"h265", "hevc"} else "h264"
    quality = re.sub(r"[^A-Za-z0-9]+", "-", str(value.get("qualityType") or "video"))
    representation_id = re.sub(
        r"[^A-Za-z0-9]+", "-", str(value.get("id") or len(media_url))
    )
    return {
        "format_id": f"{codec_name}-{quality}-{representation_id}",
        "format_note": value.get("qualityLabel"),
        "url": media_url,
        "ext": "mp4",
        "vcodec": codec_name,
        "acodec": "aac",
        "width": value.get("width"),
        "height": value.get("height"),
        "fps": value.get("frameRate"),
        "tbr": value.get("avgBitrate"),
        "filesize": value.get("fileSize"),
        "dynamic_range": "HDR" if value.get("hdrType") else "SDR",
        "http_headers": _MOBILE_HEADERS,
    }


def _first_url(value: object) -> str | None:
    if not isinstance(value, list):
        return None
    for item in value:
        candidate = item.get("url") if isinstance(item, dict) else item
        if isinstance(candidate, str) and candidate.startswith("https://"):
            return candidate
    return None


def _milliseconds(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number / 1000 if number > 0 else None
