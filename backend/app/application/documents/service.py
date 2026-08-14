"""Owner-scoped screenplay document queries."""

from __future__ import annotations

import re
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from uuid import UUID

from app.application.imports import (
    ImportApplicationError,
    ImportApplicationErrorCode,
    ImportObjectStorageError,
    ImportPersistenceConflict,
    ImportPersistenceError,
    ImportPersistenceNotFound,
    MultipartUploadNotFound,
    QuarantineObjectStorage,
)
from app.domain.imports import ImportErrorCode, ImportSourceFormat, ImportStatus

from .models import DocumentPage, DocumentPageSnapshot, DocumentSnapshot, DocumentView
from .ports import DocumentDeletionRepository, DocumentReader

_OWNER_HASH = re.compile(r"[0-9a-f]{64}")


class GetDocument:
    def __init__(self, reader: DocumentReader) -> None:
        self._reader = reader

    async def __call__(self, document_id: UUID, owner_hash: str) -> DocumentView:
        owner_hash = _owner_hash(owner_hash)
        snapshot = await self._reader.get_document(document_id, owner_hash)
        if snapshot is None or snapshot.owner_hash != owner_hash:
            raise ImportApplicationError(ImportApplicationErrorCode.NOT_FOUND)
        return _view(snapshot)


class ListDocuments:
    def __init__(self, reader: DocumentReader) -> None:
        self._reader = reader

    async def __call__(
        self, owner_hash: str, *, page: int = 1, page_size: int = 20
    ) -> DocumentPage:
        owner_hash = _owner_hash(owner_hash)
        if not 1 <= page <= 10_000 or not 1 <= page_size <= 50:
            raise ImportApplicationError(ImportApplicationErrorCode.INVALID_REQUEST)
        snapshot = await self._reader.list_documents(
            owner_hash, page=page, page_size=page_size
        )
        return _page(snapshot, owner_hash)


class DeleteDocument:
    def __init__(
        self,
        repository: DocumentDeletionRepository,
        storage: QuarantineObjectStorage,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._now = now

    async def __call__(self, document_id: UUID, owner_hash: str) -> None:
        owner_hash = _owner_hash(owner_hash)
        now = self._now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
        try:
            plan = await self._repository.prepare_document_deletion(
                document_id, owner_hash, now=now
            )
        except ImportPersistenceError as error:
            raise _persistence_error(error) from error
        if plan.document_id != document_id or plan.owner_hash != owner_hash:
            raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
        for cleanup in plan.cleanup:
            _validate_deletion_key(cleanup.object_key, document_id, plan.attempt)
        keys: list[str] = []
        for cleanup in plan.cleanup:
            try:
                if cleanup.upload_id is not None:
                    with suppress(MultipartUploadNotFound):
                        await self._storage.abort_multipart_upload(
                            cleanup.object_key, cleanup.upload_id
                        )
                await self._storage.delete(cleanup.object_key)
            except ImportObjectStorageError as error:
                raise ImportApplicationError(
                    ImportApplicationErrorCode.STORAGE_UNAVAILABLE
                ) from error
            keys.append(cleanup.object_key)
        try:
            await self._repository.finish_document_deletion(
                document_id, owner_hash, object_keys=tuple(keys), now=now
            )
        except ImportPersistenceError as error:
            raise _persistence_error(error) from error


def _owner_hash(value: str) -> str:
    if _OWNER_HASH.fullmatch(value) is None:
        raise ImportApplicationError(ImportApplicationErrorCode.INVALID_REQUEST)
    return value


def _page(snapshot: DocumentPageSnapshot, owner_hash: str) -> DocumentPage:
    if snapshot.page < 1 or snapshot.page_size < 1 or snapshot.total < 0:
        raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
    if any(item.owner_hash != owner_hash for item in snapshot.items):
        raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
    return DocumentPage(
        items=tuple(_view(item) for item in snapshot.items),
        page=snapshot.page,
        page_size=snapshot.page_size,
        total=snapshot.total,
    )


def _view(snapshot: DocumentSnapshot) -> DocumentView:
    try:
        source_format = ImportSourceFormat(snapshot.source_format)
        status = ImportStatus(snapshot.status)
        error_code = (
            None
            if snapshot.error_code is None
            else ImportErrorCode(snapshot.error_code)
        )
    except ValueError as error:
        raise ImportApplicationError(
            ImportApplicationErrorCode.INTERNAL_ERROR
        ) from error
    if source_format.content_kind.value != "screenplay":
        raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
    return DocumentView(
        id=snapshot.id,
        title=snapshot.title,
        original_filename=snapshot.original_filename,
        source_format=source_format,
        declared_size_bytes=snapshot.declared_size_bytes,
        status=status,
        attempt=snapshot.attempt,
        error_code=error_code,
        version=snapshot.version,
        detected_language=snapshot.detected_language,
        scene_count=snapshot.scene_count,
        character_count=snapshot.character_count,
        quality_warnings=snapshot.quality_warnings,
        expires_at=snapshot.expires_at,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
        finished_at=snapshot.finished_at,
    )


def _validate_deletion_key(object_key: str, document_id: UUID, attempt: int) -> None:
    for prefix, final_names in (
        (f"quarantine/screenplay/{document_id}/", {"source"}),
        (f"documents/{document_id}/", {"original", "screenplay.md"}),
    ):
        if object_key.startswith(prefix):
            parts = object_key.removeprefix(prefix).split("/")
            if (
                len(parts) == 2
                and parts[0].isdigit()
                and 1 <= int(parts[0]) <= attempt
                and parts[1] in final_names
            ):
                return
    raise ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)


def _persistence_error(error: ImportPersistenceError) -> ImportApplicationError:
    if isinstance(error, ImportPersistenceNotFound):
        return ImportApplicationError(ImportApplicationErrorCode.NOT_FOUND)
    if isinstance(error, ImportPersistenceConflict):
        return ImportApplicationError(ImportApplicationErrorCode.INVALID_STATE)
    return ImportApplicationError(ImportApplicationErrorCode.INTERNAL_ERROR)
