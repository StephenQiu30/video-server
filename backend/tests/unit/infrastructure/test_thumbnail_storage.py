from __future__ import annotations

import base64
from uuid import UUID

import pytest
from app.application.downloads import (
    GetThumbnail,
    PersistThumbnail,
    ThumbnailObject,
    ThumbnailSource,
    ThumbnailStorageError,
)
from app.infrastructure.thumbnail_storage import MinioThumbnailStorage

INSPECTION_ID = UUID("11111111-1111-4111-8111-111111111111")
OWNER = "a" * 64
PNG = b"\x89PNG\r\n\x1a\nprivate-cover"
DATA_URL = f"data:image/png;base64,{base64.b64encode(PNG).decode()}"


class MemoryMinio:
    bucket = "video-artifacts"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def upload_bytes(
        self, object_key: str, content: bytes, content_type: str, sha256: str
    ) -> int:
        del content_type, sha256
        self.objects[object_key] = content
        return len(content)

    async def read(self, object_key: str) -> bytes:
        return self.objects[object_key]


class ThumbnailRepository:
    def __init__(self) -> None:
        self.object: ThumbnailObject | None = None
        self.legacy_data_url: str | None = DATA_URL

    async def get_thumbnail_source(
        self, inspection_id: UUID, owner_hash: str
    ) -> ThumbnailSource | None:
        if inspection_id != INSPECTION_ID or owner_hash != OWNER:
            return None
        return ThumbnailSource(
            inspection_id=inspection_id,
            owner_hash=owner_hash,
            object=self.object,
            legacy_data_url=self.legacy_data_url,
        )

    async def save_thumbnail(
        self,
        inspection_id: UUID,
        owner_hash: str,
        thumbnail: ThumbnailObject,
    ) -> None:
        assert inspection_id == INSPECTION_ID
        assert owner_hash == OWNER
        self.object = thumbnail
        self.legacy_data_url = None


@pytest.mark.asyncio
async def test_thumbnail_storage_uses_content_addressed_private_object() -> None:
    minio = MemoryMinio()
    storage = MinioThumbnailStorage(minio)  # type: ignore[arg-type]

    stored = await storage.store(INSPECTION_ID, DATA_URL)

    assert stored.bucket == "video-artifacts"
    assert stored.object_key.startswith(f"thumbnails/{INSPECTION_ID}/")
    assert stored.object_key.endswith(".png")
    assert stored.content_type == "image/png"
    assert stored.size_bytes == len(PNG)
    assert await storage.read(stored) == PNG


@pytest.mark.asyncio
async def test_thumbnail_read_rejects_corrupted_object() -> None:
    minio = MemoryMinio()
    storage = MinioThumbnailStorage(minio)  # type: ignore[arg-type]
    stored = await storage.store(INSPECTION_ID, DATA_URL)
    minio.objects[stored.object_key] = b"corrupted"

    with pytest.raises(ThumbnailStorageError, match="integrity"):
        await storage.read(stored)


@pytest.mark.asyncio
async def test_get_thumbnail_lazily_migrates_legacy_inline_data() -> None:
    repository = ThumbnailRepository()
    minio = MemoryMinio()
    storage = MinioThumbnailStorage(minio)  # type: ignore[arg-type]
    persist = PersistThumbnail(repository, storage)  # type: ignore[arg-type]
    get = GetThumbnail(repository, storage, persist)  # type: ignore[arg-type]

    result = await get(INSPECTION_ID, OWNER)

    assert result.content == PNG
    assert result.content_type == "image/png"
    assert repository.object is not None
    assert repository.legacy_data_url is None


@pytest.mark.asyncio
async def test_thumbnail_storage_rejects_spoofed_or_oversized_data() -> None:
    storage = MinioThumbnailStorage(MemoryMinio())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="invalid thumbnail image"):
        await storage.store(
            INSPECTION_ID,
            f"data:image/png;base64,{base64.b64encode(b'not-a-png').decode()}",
        )
    bounded = MinioThumbnailStorage(MemoryMinio(), max_bytes=len(PNG) * 2)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="size limit"):
        await bounded.store(
            INSPECTION_ID,
            f"data:image/png;base64,{base64.b64encode(PNG * 4).decode()}",
        )
