"""Stable availability boundaries for XiaoHongShu note pages."""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

from yt_dlp.extractor.xiaohongshu import (  # type: ignore[import-untyped]
    XiaoHongShuIE,
)
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_NOTE_UNAVAILABLE = "Xiaohongshu note unavailable"
_VERIFICATION_REQUIRED = "Xiaohongshu request verification required"


class _XiaoHongShuAvailabilityIE(
    XiaoHongShuIE,  # type: ignore[misc, call-arg]
    plugin_name="availability",
):
    """Translate first-party error redirects before upstream parses empty state."""

    def _download_webpage_handle(
        self,
        url_or_request: Any,
        video_id: str | None,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[str, Any]:
        webpage, response = cast(
            tuple[str, Any],
            super()._download_webpage_handle(
                url_or_request,
                video_id,
                *args,
                **kwargs,
            ),
        )
        final_url = str(getattr(response, "url", ""))
        error = _availability_error(final_url)
        if error is not None:
            raise ExtractorError(
                error,
                video_id=video_id,
                expected=True,
            )
        return webpage, response


def _availability_error(final_url: str) -> str | None:
    parsed = urlsplit(final_url)
    if parsed.hostname not in {"xiaohongshu.com", "www.xiaohongshu.com"}:
        return None
    values = parse_qs(parsed.query).get("error_code")
    error_code = values[0] if values else None
    if error_code == "300031":
        return _NOTE_UNAVAILABLE
    if error_code == "300012":
        return _VERIFICATION_REQUIRED
    return None
