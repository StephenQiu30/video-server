from __future__ import annotations

from uuid import UUID

from app.application.downloads.errors import ApplicationError, ApplicationErrorCode
from app.application.downloads.ports import DownloadRepository, ThumbnailObjectStorage
from app.application.downloads.thumbnail import (
    ThumbnailContent,
    ThumbnailSource,
    ThumbnailStorageError,
    safe_thumbnail_data_url,
)
from app.application.downloads.validation import validate_owner_hash


class PersistThumbnail:
    def __init__(
        self, repository: DownloadRepository, storage: ThumbnailObjectStorage
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def __call__(
        self, inspection_id: UUID, owner_hash: str, data_url: str | None
    ) -> bool:
        safe_data_url = safe_thumbnail_data_url(data_url)
        if safe_data_url is None:
            return False
        stored = await self._storage.store(inspection_id, safe_data_url)
        await self._repository.save_thumbnail(
            inspection_id, validate_owner_hash(owner_hash), stored
        )
        return True


class PersistDownloadThumbnail:
    def __init__(
        self, repository: DownloadRepository, storage: ThumbnailObjectStorage
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def __call__(
        self, job_id: UUID, owner_hash: str, data_url: str | None
    ) -> bool:
        safe_data_url = safe_thumbnail_data_url(data_url)
        if safe_data_url is None:
            return False
        stored = await self._storage.store(job_id, safe_data_url)
        await self._repository.save_download_thumbnail(
            job_id, validate_owner_hash(owner_hash), stored
        )
        return True


class GetThumbnail:
    def __init__(
        self,
        repository: DownloadRepository,
        storage: ThumbnailObjectStorage,
        persist: PersistThumbnail,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._persist = persist

    async def __call__(self, inspection_id: UUID, owner_hash: str) -> ThumbnailContent:
        owner_hash = validate_owner_hash(owner_hash)
        source = await self._source(inspection_id, owner_hash)
        if source.object is None and source.legacy_data_url is not None:
            try:
                await self._persist(inspection_id, owner_hash, source.legacy_data_url)
            except ThumbnailStorageError as exc:
                raise ApplicationError(
                    ApplicationErrorCode.STORAGE_UNAVAILABLE
                ) from exc
            source = await self._source(inspection_id, owner_hash)
        if source.object is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        try:
            content = await self._storage.read(source.object)
        except ThumbnailStorageError as exc:
            raise ApplicationError(ApplicationErrorCode.STORAGE_UNAVAILABLE) from exc
        return ThumbnailContent(
            content=content,
            content_type=source.object.content_type,
            sha256=source.object.sha256,
        )

    async def _source(self, inspection_id: UUID, owner_hash: str) -> ThumbnailSource:
        source = await self._repository.get_thumbnail_source(inspection_id, owner_hash)
        if source is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        return source


class GetDownloadThumbnail:
    def __init__(
        self, repository: DownloadRepository, storage: ThumbnailObjectStorage
    ) -> None:
        self._repository = repository
        self._storage = storage

    async def __call__(self, job_id: UUID, owner_hash: str) -> ThumbnailContent:
        source = await self._repository.get_download_thumbnail_source(
            job_id, validate_owner_hash(owner_hash)
        )
        if source is None or source.object is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        try:
            content = await self._storage.read(source.object)
        except ThumbnailStorageError as exc:
            raise ApplicationError(ApplicationErrorCode.STORAGE_UNAVAILABLE) from exc
        return ThumbnailContent(
            content=content,
            content_type=source.object.content_type,
            sha256=source.object.sha256,
        )
