"""Bounded private thumbnail persistence backed by MinIO."""

from __future__ import annotations

import base64
import binascii
import hashlib
from uuid import UUID

from app.application.downloads import ThumbnailObject, ThumbnailStorageError
from app.infrastructure.object_storage import MinioObjectStorage

_MAX_BYTES = 2_000_000
_FORMATS = {
    "image/avif": "avif",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class MinioThumbnailStorage:
    def __init__(
        self, storage: MinioObjectStorage, *, max_bytes: int = _MAX_BYTES
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("thumbnail size limit must be positive")
        self._storage = storage
        self._max_bytes = max_bytes

    async def store(self, inspection_id: UUID, data_url: str) -> ThumbnailObject:
        content_type, content = _decode(data_url, self._max_bytes)
        sha256 = hashlib.sha256(content).hexdigest()
        extension = _FORMATS[content_type]
        object_key = f"thumbnails/{inspection_id}/{sha256}.{extension}"
        try:
            await self._storage.upload_bytes(object_key, content, content_type, sha256)
        except Exception as exc:
            raise ThumbnailStorageError("thumbnail upload failed") from exc
        return ThumbnailObject(
            bucket=self._storage.bucket,
            object_key=object_key,
            content_type=content_type,
            sha256=sha256,
            size_bytes=len(content),
        )

    async def read(self, thumbnail: ThumbnailObject) -> bytes:
        if thumbnail.bucket != self._storage.bucket:
            raise ThumbnailStorageError("thumbnail bucket is not configured")
        try:
            content = await self._storage.read(thumbnail.object_key)
        except Exception as exc:
            raise ThumbnailStorageError("thumbnail read failed") from exc
        digest = hashlib.sha256(content).hexdigest()
        if len(content) != thumbnail.size_bytes or digest != thumbnail.sha256:
            raise ThumbnailStorageError("thumbnail integrity check failed")
        return content


def _decode(data_url: str, max_bytes: int) -> tuple[str, bytes]:
    header, separator, encoded = data_url.partition(",")
    if (
        not separator
        or not header.startswith("data:")
        or not header.endswith(";base64")
    ):
        raise ValueError("invalid thumbnail data URL")
    content_type = header[5:-7].casefold()
    if content_type not in _FORMATS:
        raise ValueError("unsupported thumbnail content type")
    if len(encoded) > ((max_bytes + 2) // 3) * 4 + 4:
        raise ValueError("thumbnail exceeds size limit")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid thumbnail encoding") from exc
    if not content or len(content) > max_bytes or not _matches(content_type, content):
        raise ValueError("invalid thumbnail image")
    return content_type, content


def _matches(content_type: str, content: bytes) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return (
            len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
        )
    return (
        len(content) >= 12
        and content[4:8] == b"ftyp"
        and content[8:12]
        in {
            b"avif",
            b"avis",
        }
    )
