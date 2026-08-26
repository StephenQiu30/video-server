"""Bounded thumbnail retrieval isolated from media orchestration."""

from __future__ import annotations

import asyncio
import base64
from urllib.parse import urljoin

import httpx

from app.runner.errors import RunnerFailure
from app.runner.settings import RunnerSettings
from app.runner.utilities import safe_media_url

_IMAGE_TYPES = frozenset({"image/avif", "image/jpeg", "image/png", "image/webp"})
_RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class ThumbnailFetcher:
    def __init__(self, settings: RunnerSettings) -> None:
        self._max_bytes = settings.runner_max_thumbnail_bytes
        self._timeout = min(settings.runner_inspect_timeout_seconds, 15)

    async def fetch(
        self,
        thumbnail_urls: tuple[str, ...],
        *,
        referer: str,
        egress_proxy: str,
    ) -> str | None:
        if not thumbnail_urls:
            return None
        headers = {
            "Accept": "image/avif,image/webp,image/png,image/jpeg;q=0.9,*/*;q=0.5",
            "Referer": referer,
            "User-Agent": "Mozilla/5.0 (compatible; VideoDownloader/1.0)",
        }
        try:
            async with httpx.AsyncClient(
                proxy=egress_proxy,
                follow_redirects=False,
                timeout=self._timeout,
                trust_env=False,
            ) as client:
                for thumbnail_url in thumbnail_urls:
                    for attempt in range(2):
                        try:
                            result, retryable = await self._fetch_candidate(
                                client,
                                thumbnail_url,
                                headers=headers,
                            )
                        except (httpx.HTTPError, RunnerFailure, ValueError):
                            result, retryable = None, True
                        if result is not None:
                            return result
                        if not retryable or attempt == 1:
                            break
                        await asyncio.sleep(0.25)
        except (httpx.HTTPError, RunnerFailure, ValueError):
            return None
        return None

    async def _fetch_candidate(
        self,
        client: httpx.AsyncClient,
        thumbnail_url: str,
        *,
        headers: dict[str, str],
    ) -> tuple[str | None, bool]:
        current_url = thumbnail_url
        for _ in range(4):
            safe_media_url(current_url)
            async with client.stream("GET", current_url, headers=headers) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        return None, False
                    current_url = urljoin(current_url, location)
                    continue
                if response.status_code != 200:
                    return None, response.status_code in _RETRYABLE_STATUS
                media_type = (
                    response.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                if media_type not in _IMAGE_TYPES:
                    return None, False
                content_length = response.headers.get("content-length")
                if content_length is not None and int(content_length) > self._max_bytes:
                    return None, False
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > self._max_bytes:
                        return None, False
                if not content:
                    return None, False
                encoded = base64.b64encode(content).decode("ascii")
                return f"data:{media_type};base64,{encoded}", False
        return None, False
