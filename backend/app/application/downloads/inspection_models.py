from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.downloads import DownloadPlan
from app.domain.providers import ProviderAccessContextRef


@dataclass(frozen=True, slots=True)
class EncryptedUrl:
    ciphertext: bytes
    nonce: bytes
    key_id: str

    def __post_init__(self) -> None:
        if not self.ciphertext or not self.nonce or not self.key_id.strip():
            raise ValueError("encrypted URL envelope is incomplete")


@dataclass(frozen=True, slots=True)
class RunnerFormat:
    display_name: str
    plan: DownloadPlan


@dataclass(frozen=True, slots=True)
class RunnerInspection:
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    formats: tuple[RunnerFormat, ...]
    access_context: ProviderAccessContextRef
    thumbnail_data_url: str | None = None


@dataclass(frozen=True, slots=True)
class FormatCreate:
    id: UUID
    display_name: str
    plan_fingerprint: str
    semantic_plan: dict[str, object]
    provider_hints: dict[str, object]
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
    metadata: dict[str, object]
    expires_at: datetime
    formats: tuple[FormatCreate, ...]


@dataclass(frozen=True, slots=True)
class FormatSnapshot:
    id: UUID
    display_name: str
    plan_fingerprint: str
    semantic_plan: dict[str, object]
    provider_hints: dict[str, object]
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
    metadata: dict[str, object]
    expires_at: datetime
    formats: tuple[FormatSnapshot, ...]


@dataclass(frozen=True, slots=True)
class InspectionSaveResult:
    inspection: InspectionSnapshot
    created: bool


@dataclass(frozen=True, slots=True)
class FormatView:
    id: UUID
    display_name: str
    plan: DownloadPlan


@dataclass(frozen=True, slots=True)
class InspectionView:
    id: UUID
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    expires_at: datetime
    formats: tuple[FormatView, ...]
    thumbnail_url: str | None = None
