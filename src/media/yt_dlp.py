"""Constrained yt-dlp adapter used by the inspect and worker paths."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.media.formats import FormatPolicyError, NormalizedFormat, normalize_formats
from src.media.url_policy import URLPolicy, UrlPolicyError


class MediaExtractionError(RuntimeError):
    """Base error for stable media-inspection failures."""


class UnsupportedMediaError(MediaExtractionError):
    """The URL is valid, but the public single-video policy rejects it."""


class MediaLimitError(MediaExtractionError):
    """The media exceeds the configured duration/format limits."""


class MediaInspectTimeout(MediaExtractionError):
    """yt-dlp did not complete within the configured timeout."""


@dataclass(frozen=True, slots=True)
class InspectResult:
    source_url: str
    extractor_key: str
    external_id: str | None
    title: str
    thumbnail_url: str | None
    duration_seconds: int | None
    formats: tuple[NormalizedFormat, ...]


def _clean_title(value: object) -> str:
    title = " ".join(str(value or "Untitled video").split())
    return title[:500] or "Untitled video"


def _extractor_key(info: Mapping[str, Any]) -> str:
    return str(info.get("extractor_key") or info.get("extractor") or "").strip()


def _is_single_video(info: Mapping[str, Any]) -> bool:
    if info.get("_type") not in (None, "video"):
        return False
    if isinstance(info.get("entries"), (list, tuple)):
        return False
    if info.get("playlist_count") or info.get("playlist_index"):
        return False
    return True


class YtdlpExtractor:
    """A deliberately small, non-configurable yt-dlp surface.

    No caller-controlled yt-dlp options are accepted.  This prevents selector,
    cookie, header, proxy and output-path injection through the HTTP API.
    """

    def __init__(
        self,
        *,
        allowed_extractors: tuple[str, ...] = ("default",),
        timeout_seconds: int = 30,
        max_duration_seconds: int = 7200,
        policy: URLPolicy | None = None,
        ytdlp_class: type[Any] | None = None,
    ) -> None:
        self.allowed_extractors = tuple(item.lower() for item in allowed_extractors)
        self.timeout_seconds = timeout_seconds
        self.max_duration_seconds = max_duration_seconds
        self.policy = policy or URLPolicy()
        self._ytdlp_class = ytdlp_class

    def _client_class(self) -> type[Any]:
        if self._ytdlp_class is not None:
            return self._ytdlp_class
        try:
            from yt_dlp import YoutubeDL  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - dependency is locked
            raise MediaExtractionError("yt-dlp dependency is unavailable") from exc
        return YoutubeDL  # type: ignore[no-any-return]

    def _options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "ignoreconfig": True,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": self.timeout_seconds,
            "retries": 0,
            "fragment_retries": 0,
            "continuedl": False,
        }
        if self.allowed_extractors and self.allowed_extractors != ("default",):
            options["allowed_extractors"] = list(self.allowed_extractors)
        return options

    def inspect(self, url: str) -> InspectResult:
        try:
            validated = self.policy.validate(url)
        except UrlPolicyError as exc:
            raise UnsupportedMediaError(str(exc)) from exc
        try:
            with self._client_class()(self._options()) as client:
                info = client.extract_info(validated.value, download=False)
        except UnsupportedMediaError:
            raise
        except Exception as exc:
            # Do not expose the provider's URL, cookies or local paths in API
            # errors.  The original exception remains available for logs.
            name = exc.__class__.__name__.lower()
            if "timeout" in name or "timedout" in name:
                raise MediaInspectTimeout("media inspection timed out") from exc
            raise MediaExtractionError("media inspection failed") from exc
        if not isinstance(info, Mapping):
            raise UnsupportedMediaError("extractor did not return a video")
        return self._normalize(validated.value, info)

    def _normalize(self, source_url: str, info: Mapping[str, Any]) -> InspectResult:
        key = _extractor_key(info)
        if not key or key.lower() == "generic":
            raise UnsupportedMediaError("generic extractor is not supported")
        if self.allowed_extractors != ("default",):
            allowed = {item.lower() for item in self.allowed_extractors}
            if key.lower() not in allowed:
                raise UnsupportedMediaError("extractor is not enabled")
        if not _is_single_video(info):
            raise UnsupportedMediaError("only one public video is supported")
        live_status = str(info.get("live_status") or "").lower()
        if bool(info.get("is_live")) or live_status in {"is_live", "post_live"}:
            raise UnsupportedMediaError("live streams are not supported")
        if bool(info.get("has_drm")) or bool(info.get("drm")):
            raise UnsupportedMediaError("DRM media is not supported")
        duration = None
        if info.get("duration") is not None:
            try:
                duration = int(float(info["duration"]))
            except (TypeError, ValueError) as exc:
                raise UnsupportedMediaError("media duration is invalid") from exc
            if duration <= 0:
                duration = None
            elif duration > self.max_duration_seconds:
                raise MediaLimitError("media duration exceeds the configured limit")
        try:
            formats = tuple(normalize_formats(info))
        except FormatPolicyError as exc:
            raise UnsupportedMediaError(str(exc)) from exc
        return InspectResult(
            source_url=source_url,
            extractor_key=key,
            external_id=(str(info["id"]) if info.get("id") is not None else None),
            title=_clean_title(info.get("title")),
            thumbnail_url=(str(info["thumbnail"]) if info.get("thumbnail") else None),
            duration_seconds=duration,
            formats=formats,
        )

    async def inspect_async(self, url: str) -> InspectResult:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.inspect, url), timeout=self.timeout_seconds
            )
        except TimeoutError as exc:
            raise MediaInspectTimeout("media inspection timed out") from exc


__all__ = [
    "InspectResult",
    "MediaExtractionError",
    "MediaInspectTimeout",
    "MediaLimitError",
    "UnsupportedMediaError",
    "YtdlpExtractor",
]
