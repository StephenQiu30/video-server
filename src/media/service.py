"""Application service for the public media-inspection operation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from src.downloads.repository import DownloadRepository
from src.media.yt_dlp import YtdlpExtractor


class MediaInspectionService:
    """Parse one URL and persist the short-lived source/format snapshot."""

    def __init__(
        self,
        session_factory: Any,
        extractor: YtdlpExtractor,
        *,
        inspect_ttl_seconds: int = 900,
    ) -> None:
        self.session_factory = session_factory
        self.extractor = extractor
        self.inspect_ttl_seconds = inspect_ttl_seconds

    async def inspect_media(self, *, url: str, owner_token_hash: str) -> Any:
        result = await self.extractor.inspect_async(url)
        expires_at = datetime.now(UTC) + timedelta(seconds=self.inspect_ttl_seconds)
        async with self.session_factory() as session:
            repository = DownloadRepository(session)
            source = await repository.add_source(
                owner_token_hash=owner_token_hash,
                source_url=result.source_url,
                source_host=(urlsplit(result.source_url).hostname or "")[:253],
                extractor_key=result.extractor_key,
                external_id=result.external_id,
                title=result.title,
                thumbnail_url=result.thumbnail_url,
                duration_seconds=result.duration_seconds,
                inspect_expires_at=expires_at,
                formats=[item.to_model_values() for item in result.formats],
            )
            await session.commit()
            return source


__all__ = ["MediaInspectionService"]
