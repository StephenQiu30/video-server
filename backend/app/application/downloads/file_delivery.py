"""HTTP delivery metadata for completed video artifacts."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import quote

from app.domain.downloads import Container


def download_disposition(object_key: str, title: str | None) -> str:
    """Build an RFC 6266 attachment disposition using the video title."""
    fallback = _download_filename(object_key)
    clean_title = _sanitize_filename(title) if title else ""
    if not clean_title:
        return f'attachment; filename="{fallback}"'
    extension = PurePosixPath(object_key).suffix
    encoded_name = f"{clean_title}{extension}"
    if encoded_name.isascii():
        return f'attachment; filename="{encoded_name}"'
    return (
        f'attachment; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(encoded_name, safe='')}"
    )


def _download_filename(object_key: str) -> str:
    suffix = PurePosixPath(object_key).suffix.casefold()
    supported = {f".{container.value}" for container in Container}
    return f"video{suffix}" if suffix in supported else "download"


def _sanitize_filename(title: str) -> str:
    value = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', "", title).strip()
    return value[:128].rstrip(".") if value else ""
