"""Primitive persistence contracts; domain and SQLAlchemy remain decoupled."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FormatCreate:
    id: UUID
    display_name: str
    plan_fingerprint: str
    semantic_plan: dict[str, Any]
    provider_hints: dict[str, Any]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class InspectionCreate:
    id: UUID
    owner_hash: str
    idempotency_key: str
    request_fingerprint: str
    url_ciphertext: bytes
    url_nonce: bytes
    url_key_id: str
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    metadata: dict[str, Any]
    expires_at: datetime
    formats: tuple[FormatCreate, ...]


@dataclass(frozen=True, slots=True)
class FormatSnapshot:
    id: UUID
    display_name: str
    plan_fingerprint: str
    semantic_plan: dict[str, Any]
    provider_hints: dict[str, Any]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class InspectionSnapshot:
    id: UUID
    owner_hash: str
    request_fingerprint: str
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    metadata: dict[str, Any]
    expires_at: datetime
    formats: tuple[FormatSnapshot, ...]


@dataclass(frozen=True, slots=True)
class InspectionCreateResult:
    inspection: InspectionSnapshot
    created: bool


@dataclass(frozen=True, slots=True)
class DownloadCreate:
    id: UUID
    inspection_id: UUID
    format_id: UUID
    owner_hash: str
    idempotency_key: str
    request_fingerprint: str
    semantic_plan: dict[str, Any]
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class ArtifactCreate:
    bucket: str
    sha256: str
    size_bytes: int
    duration_ms: int
    container: str
    content_type: str
    media_metadata: dict[str, Any]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class JobSourceSnapshot:
    job_id: UUID
    inspection_id: UUID
    semantic_plan: dict[str, Any]
    provider_hints: dict[str, Any]
    extractor_key: str
    provider_media_id: str
    access_context: dict[str, Any]
    url_ciphertext: bytes
    url_nonce: bytes
    url_key_id: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class JobSnapshot:
    id: UUID
    inspection_id: UUID
    format_id: UUID
    owner_hash: str
    request_fingerprint: str
    semantic_plan: dict[str, Any]
    status: str
    stage: str | None
    progress: int
    attempt: int
    max_attempts: int
    version: int
    lease_owner: str | None
    lease_expires_at: datetime | None
    heartbeat_at: datetime | None
    started_at: datetime | None
    retry_at: datetime | None
    finished_at: datetime | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class JobCreateResult:
    job: JobSnapshot
    created: bool


@dataclass(frozen=True, slots=True)
class DownloadHistoryItemSnapshot:
    id: UUID
    title: str
    thumbnail_url: str | None
    format_name: str
    status: str
    progress: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class DownloadHistorySummarySnapshot:
    total: int
    succeeded: int
    active: int
    failed: int


@dataclass(frozen=True, slots=True)
class DownloadHistoryPageSnapshot:
    items: tuple[DownloadHistoryItemSnapshot, ...]
    page: int
    page_size: int
    total: int
    summary: DownloadHistorySummarySnapshot


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    id: UUID
    job_id: UUID
    attempt: int
    bucket: str
    object_key: str
    sha256: str
    size_bytes: int
    duration_ms: int
    container: str
    content_type: str
    media_metadata: dict[str, Any]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ArtifactPurgeResult:
    deleted: int
    failed: int


@dataclass(frozen=True, slots=True)
class OutboxSnapshot:
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: dict[str, Any]
    publish_attempts: int
    available_at: datetime
    created_at: datetime
