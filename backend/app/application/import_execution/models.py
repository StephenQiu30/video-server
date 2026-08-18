from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID

from app.domain.documents import ScreenplayScene
from app.domain.imports import ContentKind, ImportSourceFormat


@dataclass(frozen=True, slots=True)
class ImportVerificationClaim:
    resource_id: UUID
    content_kind: ContentKind
    source_format: ImportSourceFormat
    attempt: int
    version: int
    object_key: str = field(repr=False)
    declared_size_bytes: int
    declared_sha256: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class VerifiedImportArtifact:
    sha256: str
    size_bytes: int
    duration_ms: int
    container: str
    content_type: str
    media_metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class VerifiedDocumentImport:
    original_sha256: str
    original_size_bytes: int
    original_content_type: str
    normalized_path: Path = field(repr=False)
    normalized_sha256: str = field(repr=False)
    normalized_size_bytes: int
    detected_language: str
    character_count: int
    scenes: tuple[ScreenplayScene, ...]
    quality_warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImportExecutionSettings:
    worker_id: str
    bucket: str
    workspace_root: Path
    lease_for: timedelta
    heartbeat_interval: float

    def __post_init__(self) -> None:
        if not self.worker_id.strip() or not self.bucket.strip():
            raise ValueError("worker id and bucket cannot be blank")
        if self.lease_for.total_seconds() <= 0 or self.heartbeat_interval <= 0:
            raise ValueError("lease and heartbeat interval must be positive")
        if self.heartbeat_interval >= self.lease_for.total_seconds():
            raise ValueError("heartbeat interval must be shorter than the lease")
        object.__setattr__(self, "workspace_root", self.workspace_root.resolve())


@dataclass(frozen=True, slots=True)
class ImportWorkspace:
    path: Path
    input_path: Path
