from __future__ import annotations

_MAX_THUMBNAIL_DATA_URL_LENGTH = 2_100_000
_SAFE_THUMBNAIL_PREFIXES = (
    "data:image/avif;base64,",
    "data:image/jpeg;base64,",
    "data:image/png;base64,",
    "data:image/webp;base64,",
)


def safe_thumbnail_data_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > _MAX_THUMBNAIL_DATA_URL_LENGTH:
        return None
    return value if value.startswith(_SAFE_THUMBNAIL_PREFIXES) else None
