from __future__ import annotations

from typing import Any

from yt_dlp.extractor.tiktok import TikTokIE  # type: ignore[import-untyped]


class _TikTokBrowserSessionIE(TikTokIE, plugin_name="browser_session"):  # type: ignore[misc, call-arg]
    """Use TikTok's challenge page instead of its empty impersonated response.

    TikTok currently returns a small, non-actionable WAF document when yt-dlp
    requests the video page with transport impersonation enabled. The regular
    request path returns the challenge document that yt-dlp already knows how
    to solve. Cookie handling and all extraction logic remain upstream-owned.
    """

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
