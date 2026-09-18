"""Preserve provider media identity for the common image/video pipeline."""

from __future__ import annotations

from typing import Any, cast

from yt_dlp.extractor.instagram import InstagramIE  # type: ignore[import-untyped]


class _InstagramMediaIE(InstagramIE, plugin_name="media_identity"):  # type: ignore[misc, call-arg]
    def _extract_product_media(self, product_media: dict[str, Any]) -> dict[str, Any]:
        result = cast(dict[str, Any], super()._extract_product_media(product_media))
        # Instagram's media discriminator: 1 = photo, 2 = video.
        # Keep this translation at the provider boundary, never in download/UI.
        media_type = product_media.get("media_type")
        if media_type == 1 and not result.get("formats"):
            result["media_type"] = "image"
        elif media_type == 2 or result.get("formats"):
            result["media_type"] = "video"
        return result
