"""HTTP delivery metadata for completed video artifacts."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import quote

from app.domain.downloads import Container


def download_disposition(object_key: str, title: str | None) -> str:
    """Build an RFC 6266 attachment disposition using the video title."""
    fallback = _download_filename(object_key)
    filename = download_filename(object_key, title)
    if filename == fallback:
        return f'attachment; filename="{fallback}"'
    if filename.isascii():
        return f'attachment; filename="{filename}"'
    return (
        f'attachment; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


def download_filename(object_key: str, title: str | None) -> str:
    """Return the user-facing filename for a persisted media artifact."""
    fallback = _download_filename(object_key)
    clean_title = _sanitize_filename(title) if title else ""
    if not clean_title:
        return fallback
    return f"{clean_title}{PurePosixPath(object_key).suffix}"


def _download_filename(object_key: str) -> str:
    suffix = PurePosixPath(object_key).suffix.casefold()
    supported = {f".{container.value}" for container in Container}
    return f"video{suffix}" if suffix in supported else "video.bin"


def _sanitize_filename(title: str) -> str:
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', "", title)
    value = re.sub(r"\s+", " ", value).strip().rstrip(". ")
    return value[:128].rstrip(". ") if value else ""
