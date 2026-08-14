"""Application snapshots and public views for screenplay documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.application.imports import ImportCleanupRef
from app.domain.imports import ImportErrorCode, ImportSourceFormat, ImportStatus


@dataclass(frozen=True, slots=True)
class DocumentTextArtifactSnapshot:
    bucket: str
    object_key: str = field(repr=False)
    size_bytes: int
    sha256: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    id: UUID
    owner_hash: str = field(repr=False)
    title: str = field(repr=False)
    original_filename: str = field(repr=False)
    source_format: str
    declared_size_bytes: int
    status: str
    attempt: int
    error_code: str | None
    version: int
    detected_language: str | None
    scene_count: int | None
    character_count: int | None
    text_sha256: str | None = field(repr=False)
    quality_warnings: tuple[str, ...]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    normalized_artifact: DocumentTextArtifactSnapshot | None = None


@dataclass(frozen=True, slots=True)
class DocumentPageSnapshot:
    items: tuple[DocumentSnapshot, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class DocumentView:
    id: UUID
    title: str
    original_filename: str
    source_format: ImportSourceFormat
    declared_size_bytes: int
    status: ImportStatus
    attempt: int
    error_code: ImportErrorCode | None
    version: int
    detected_language: str | None
    scene_count: int | None
    character_count: int | None
    quality_warnings: tuple[str, ...]
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    preview: str | None = None
    preview_truncated: bool = False


@dataclass(frozen=True, slots=True)
class DocumentPage:
    items: tuple[DocumentView, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class DocumentDeletionPlan:
    document_id: UUID
    owner_hash: str = field(repr=False)
    attempt: int
    cleanup: tuple[ImportCleanupRef, ...] = ()
