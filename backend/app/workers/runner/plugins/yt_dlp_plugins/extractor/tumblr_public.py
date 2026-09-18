from __future__ import annotations

from typing import Any, cast

from yt_dlp.extractor.tumblr import TumblrIE  # type: ignore[import-untyped]
from yt_dlp.utils import int_or_none  # type: ignore[import-untyped]

_PUBLIC_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}


class _TumblrPublicPageIE(TumblrIE, plugin_name="public_page"):  # type: ignore[misc, call-arg]
    """Read current public Tumblr post metadata before using the legacy path."""

    def _real_extract(self, url: str) -> dict[str, Any]:
        blog_1, blog_2, video_id = self._match_valid_url(url).groups()
        if blog_1.casefold() == "www" and blog_2:
            webpage = self._download_webpage(
                url,
                video_id,
                note="Downloading current Tumblr public post",
                fatal=False,
                headers=_PUBLIC_HEADERS,
            )
            video_url = (
                self._og_search_video_url(webpage, default=None) if webpage else None
            )
            if video_url:
                return {
                    "id": video_id,
                    "title": self._og_search_title(webpage, default=blog_2),
                    "description": self._og_search_description(webpage, default=None),
                    "uploader_id": blog_2,
                    "uploader_url": f"https://{blog_2}.tumblr.com/",
                    "formats": [
                        {
                            "url": video_url,
                            "ext": "mp4",
                            "width": int_or_none(
                                self._og_search_property(
                                    "video:width", webpage, default=None
                                )
                            ),
                            "height": int_or_none(
                                self._og_search_property(
                                    "video:height", webpage, default=None
                                )
                            ),
                        }
                    ],
                    "thumbnail": self._og_search_thumbnail(webpage, default=None),
                }

        return cast(dict[str, Any], super()._real_extract(url))
