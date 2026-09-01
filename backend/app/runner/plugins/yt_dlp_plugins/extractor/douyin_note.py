"""Extractor for public Douyin image-note share pages."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlsplit

from yt_dlp.extractor.tiktok import DouyinIE  # type: ignore[import-untyped]
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_NOTE_URL = r"https?://(?:www\.)?(?:douyin|iesdouyin)\.com/(?:share/)?note/(?P<id>\d+)/?(?:[?#].*)?$"
_SLIDES_INFO = "https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/"
_ITEM_INFO = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"
_SHARE_PAGE = "https://www.iesdouyin.com/share/note/{note_id}/"
_NOTE_UNAVAILABLE = "Douyin official note content unavailable"
_HEADERS = {
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    ),
}


class DouyinNoteIE(DouyinIE):  # type: ignore[misc]
    """Read the public media exposed by Douyin's note share page."""

    IE_NAME = "DouyinNote"
    _VALID_URL = _NOTE_URL

    def _real_extract(self, url: str) -> dict[str, Any]:
        note_id = self._match_id(url)
        share_query = _share_query(url)
        item = self._slides_item(note_id, share_query)
        if item is None:
            item = self._item_info_item(note_id, share_query)
        if item is None:
            item = self._share_page_item(note_id, urlsplit(url).query)
        if item is None:
            raise ExtractorError(_NOTE_UNAVAILABLE, video_id=note_id, expected=True)

        assets = _image_assets(item)
        if assets:
            title = " ".join(str(item.get("desc") or item.get("title") or "").split())
            return {
                "id": note_id,
                "title": title or note_id,
                "media_kind": "image_gallery",
                "assets": assets,
                "thumbnail": assets[0]["url"],
            }

        if _has_video(item):
            try:
                info = self._parse_aweme_video_app(item)
            except (AttributeError, KeyError, TypeError, ValueError):
                info = {}
            formats = info.get("formats")
            has_selected_url = isinstance(info.get("url"), str)
            has_format_url = isinstance(formats, list) and any(
                isinstance(media_format, dict)
                and isinstance(media_format.get("url"), str)
                and bool(media_format["url"])
                for media_format in formats
            )
            if has_selected_url or has_format_url:
                normalized = dict(info)
                normalized["id"] = note_id
                normalized["title"] = " ".join(
                    str(item.get("desc") or info.get("title") or note_id).split()
                )
                return normalized

        raise ExtractorError(_NOTE_UNAVAILABLE, video_id=note_id, expected=True)

    def _slides_item(
        self, note_id: str, share_query: dict[str, str]
    ) -> dict[str, Any] | None:
        query = {
            **share_query,
            "aweme_ids": note_id,
            "aweme_type": "68",
            "aid": "1128",
            "request_source": "note",
        }
        payload = self._download_json(
            _SLIDES_INFO,
            note_id,
            note="Downloading Douyin public image note",
            fatal=False,
            headers=_HEADERS,
            query=query,
        )
        return _find_item(payload, note_id)

    def _item_info_item(
        self, note_id: str, share_query: dict[str, str]
    ) -> dict[str, Any] | None:
        query = {**share_query, "item_ids": note_id, "aweme_type": "68", "aid": "1128"}
        payload = self._download_json(
            _ITEM_INFO,
            note_id,
            note="Downloading Douyin public image note metadata",
            fatal=False,
            headers=_HEADERS,
            query=query,
        )
        return _find_item(payload, note_id)

    def _share_page_item(self, note_id: str, query: str) -> dict[str, Any] | None:
        share_url = _SHARE_PAGE.format(note_id=note_id)
        if query:
            share_url = f"{share_url}?{query}"
        webpage = self._download_webpage(
            share_url,
            note_id,
            note="Downloading Douyin image note share page",
            fatal=False,
            headers=_HEADERS,
        )
        if not webpage:
            return None
        router_data = self._search_json(
            r"window\._ROUTER_DATA\s*=\s*",
            webpage,
            "Douyin router data",
            note_id,
            fatal=False,
        )
        if not isinstance(router_data, dict):
            return None
        loader_data = router_data.get("loaderData")
        if not isinstance(loader_data, dict):
            return None
        return _find_item(loader_data, note_id)


def _find_item(payload: object, expected_id: str) -> dict[str, Any] | None:
    """Find a note item across the public API's changing response wrappers."""
    if isinstance(payload, dict):
        if str(payload.get("aweme_id")) == expected_id and (
            _image_assets(payload) or _has_video(payload)
        ):
            return payload
        for key in (
            "aweme_details",
            "item_list",
            "aweme_detail",
            "item",
            "note_info",
            "noteInfo",
            "noteInfoRes",
            "videoInfoRes",
        ):
            nested = payload.get(key)
            item = _find_item(nested, expected_id)
            if item is not None:
                return item
        if _image_assets(payload) or _has_video(payload):
            return payload
        return None
    if isinstance(payload, list):
        for value in payload:
            item = _find_item(value, expected_id)
            if item is not None:
                return item
    return None


def _share_query(url: str) -> dict[str, str]:
    return {
        key: value
        for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=False)
        if key not in {"aweme_ids", "aweme_type", "aid", "request_source"}
    }


def _has_video(item: dict[str, Any]) -> bool:
    video = item.get("video")
    return isinstance(video, dict) and bool(video)


def _image_assets(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw_images: object = None
    for key in ("images", "image_list", "image_infos", "imageInfo", "image_info"):
        candidate = item.get(key)
        if isinstance(candidate, (list, dict)) and candidate:
            raw_images = candidate
            break
    if isinstance(raw_images, dict):
        raw_images = [raw_images]
    if not isinstance(raw_images, list):
        return []

    assets: list[dict[str, Any]] = []
    for raw in raw_images:
        image = raw if isinstance(raw, dict) else {"url": raw}
        url = _best_url(image)
        if url is None:
            continue
        extension = _extension(image, url)
        assets.append(
            {
                "url": url,
                "extension": extension,
                "width": image.get("width") or image.get("image_width"),
                "height": image.get("height") or image.get("image_height"),
            }
        )
    return assets


def _best_url(image: dict[str, Any]) -> str | None:
    for key in (
        "url_list",
        "download_url_list",
        "origin_url_list",
        "display_image",
        "origin_url",
        "url",
    ):
        value = image.get(key)
        if isinstance(value, list):
            urls = [item for item in value if isinstance(item, str) and item]
            if urls:
                return urls[-1]
        if isinstance(value, str) and value:
            return value
    return None


def _extension(image: dict[str, Any], url: str) -> str:
    mime = str(image.get("mime_type") or image.get("content_type") or "").casefold()
    if "png" in mime:
        return "png"
    if "webp" in mime:
        return "webp"
    suffix = urlsplit(url).path.rsplit("/", 1)[-1].split(".")[-1].casefold()
    return suffix if suffix in {"jpg", "jpeg", "png", "webp"} else "jpg"
