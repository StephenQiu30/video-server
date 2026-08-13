from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

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


def thumbnail_resource_url(inspection_id: UUID) -> str:
    return f"/api/inspections/{inspection_id}/thumbnail"


@dataclass(frozen=True, slots=True)
class ThumbnailObject:
    bucket: str
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ThumbnailSource:
    inspection_id: UUID
    owner_hash: str
    object: ThumbnailObject | None
    legacy_data_url: str | None


@dataclass(frozen=True, slots=True)
class ThumbnailContent:
    content: bytes
    content_type: str
    sha256: str


class ThumbnailStorageError(RuntimeError):
    """Private thumbnail object storage could not complete an operation."""
