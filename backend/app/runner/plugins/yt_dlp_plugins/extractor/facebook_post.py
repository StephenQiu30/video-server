from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any, cast
from urllib.parse import urlsplit

from yt_dlp.extractor.common import InfoExtractor  # type: ignore[import-untyped]
from yt_dlp.extractor.facebook import FacebookIE  # type: ignore[import-untyped]
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_FACEBOOK_HOSTS = frozenset(
    {"facebook.com", "www.facebook.com", "web.facebook.com", "m.facebook.com"}
)
_POST_PATH = re.compile(
    r"^/groups/[^/]+/(?:permalink|posts)/(?P<id>pfbid[A-Za-z0-9]+|[0-9]+)(?:/|$)"
)
_MEDIA_UNSUPPORTED = (
    "Facebook image and multi-asset posts are not supported by the video runner"
)
_SCHEMA_UNAVAILABLE = "Facebook post media structure could not be identified"
_LINK_UNAVAILABLE = "Facebook sharing link unavailable"


class FacebookPostIE(InfoExtractor):  # type: ignore[misc]
    """Resolve Facebook post shares before delegating a single video upstream."""

    IE_NAME = "facebook:post"
    _VALID_URL = r"""(?x)https?://(?:(?:www|web|m)\.)?facebook\.com/(?:
        share/p/(?P<share_id>[A-Za-z0-9_-]+)(?:/|$)
        |groups/[^/]+/(?:permalink|posts)/(?P<post_id>pfbid[A-Za-z0-9]+|[0-9]+)(?:/|$)
    )"""

    def _real_extract(self, url: str) -> dict[str, Any]:
        match = self._match_valid_url(url)
        expected_post_id = match.group("post_id")
        display_id = expected_post_id or match.group("share_id")
        webpage, response = self._download_webpage_handle(
            url,
            display_id,
            note="Resolving Facebook post share",
        )
        final_url = str(getattr(response, "url", url))
        final_post_id = _facebook_post_id(final_url)
        if final_post_id is None or not _is_facebook_url(final_url):
            raise ExtractorError(_LINK_UNAVAILABLE, expected=True)
        if expected_post_id is not None and final_post_id != expected_post_id:
            raise ExtractorError(_LINK_UNAVAILABLE, expected=True)

        media = _post_media(self, webpage, final_post_id)
        if media is None:
            raise ExtractorError(_SCHEMA_UNAVAILABLE)
        if len(media) != 1 or media[0].get("__typename") != "Video":
            raise ExtractorError(_MEDIA_UNSUPPORTED, expected=True)

        video_id = media[0].get("id")
        if not isinstance(video_id, str) or not re.fullmatch(
            r"pfbid[A-Za-z0-9]+|[0-9]+", video_id
        ):
            raise ExtractorError(_SCHEMA_UNAVAILABLE)
        return cast(
            dict[str, Any],
            self.url_result(
                f"facebook:{video_id}",
                ie=FacebookIE.ie_key(),
                video_id=video_id,
            ),
        )


def _is_facebook_url(url: str) -> bool:
    return (urlsplit(url).hostname or "").casefold() in _FACEBOOK_HOSTS


def _facebook_post_id(url: str) -> str | None:
    match = _POST_PATH.match(urlsplit(url).path)
    return match.group("id") if match is not None else None


def _post_media(
    extractor: FacebookPostIE, webpage: str, video_id: str
) -> list[dict[str, Any]] | None:
    for raw_json in re.findall(r"data-sjs>({.*?})</script>", webpage, re.DOTALL):
        payload = extractor._parse_json(raw_json, video_id, fatal=False)
        for node in _story_nodes(payload):
            attachments = node.get("attachments")
            if not isinstance(attachments, list):
                continue
            media = _attachment_media(attachments)
            if media:
                return media
    return None


def _story_nodes(value: object) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"node", "node_v2"} and isinstance(child, dict):
                yield child
            yield from _story_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _story_nodes(child)


def _attachment_media(attachments: list[object]) -> list[dict[str, Any]]:
    media: list[dict[str, Any]] = []
    seen: set[tuple[object, object]] = set()
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        candidates = (
            attachment.get("media"),
            attachment.get("target"),
            _nested_media(attachment, "styles", "attachment", "media"),
        )
        for candidate in candidates:
            if not isinstance(candidate, dict) or candidate.get("__typename") not in {
                "Photo",
                "Video",
            }:
                continue
            identity = (candidate.get("__typename"), candidate.get("id"))
            if identity in seen:
                continue
            seen.add(identity)
            media.append(candidate)
    return media


def _nested_media(value: dict[str, Any], *path: str) -> object:
    current: object = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
