from __future__ import annotations

from typing import Any, cast
from urllib.parse import urlsplit

from app.runner.errors import RunnerFailure
from app.runner.plugins.yt_dlp_plugins.extractor.tiktok_player_payload import (
    PLAYER_SCHEMA_CHANGED,
    PLAYER_TEMPORARY,
    PLAYER_UNAVAILABLE,
    player_failure,
    player_info,
)
from app.runner.provider_normalizers import tiktok_url
from yt_dlp.extractor.tiktok import (  # type: ignore[import-untyped]
    TikTokIE,
    TikTokVMIE,
)
from yt_dlp.networking import HEADRequest  # type: ignore[import-untyped]
from yt_dlp.networking.exceptions import (  # type: ignore[import-untyped]
    RequestError,
)
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

_PLAYER_API = "https://www.tiktok.com/player/api/v1/items"
_PLAYER_URL = "https://www.tiktok.com/player/v1/{video_id}"


class _TikTokPublicPlayerIE(TikTokIE, plugin_name="public_player"):  # type: ignore[misc, call-arg]
    """Resolve public video metadata only through TikTok's first-party player."""

    def _real_extract(self, url: str) -> dict[str, Any]:
        video_id, _ = self._match_valid_url(url).group("id", "user_id")
        player_url = _PLAYER_URL.format(video_id=video_id)
        try:
            payload = self._download_json(
                _PLAYER_API,
                video_id,
                note="Downloading TikTok player metadata",
                query={"item_ids": video_id},
                headers={"Referer": player_url},
            )
        except ExtractorError as exc:
            message = (
                PLAYER_TEMPORARY
                if isinstance(exc.cause, RequestError)
                else PLAYER_SCHEMA_CHANGED
            )
            raise player_failure(message, video_id) from exc
        return player_info(payload, video_id, player_url)


class _TikTokPublicShortIE(TikTokVMIE, plugin_name="public_short"):  # type: ignore[misc, call-arg]
    """Resolve official short links only when they target a public video."""

    def _real_extract(self, url: str) -> dict[str, Any]:
        video_id = self._match_id(url)
        try:
            response = self._request_webpage(
                HEADRequest(url),
                video_id,
                note="Resolving TikTok public video link",
            )
        except ExtractorError as exc:
            message = (
                PLAYER_TEMPORARY
                if isinstance(exc.cause, RequestError)
                else PLAYER_SCHEMA_CHANGED
            )
            raise player_failure(message, video_id) from exc
        redirected = getattr(response, "url", None)
        if not isinstance(redirected, str):
            raise player_failure(PLAYER_SCHEMA_CHANGED, video_id)
        try:
            normalized = tiktok_url(redirected, urlsplit(redirected))
        except RunnerFailure as exc:
            raise player_failure(PLAYER_UNAVAILABLE, video_id) from exc
        if not _TikTokPublicPlayerIE.suitable(normalized):
            raise player_failure(PLAYER_UNAVAILABLE, video_id)
        return cast(
            dict[str, Any],
            self.url_result(normalized, ie=_TikTokPublicPlayerIE.ie_key()),
        )
