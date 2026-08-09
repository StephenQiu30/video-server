from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from uuid import UUID


class AnalysisDisposition(StrEnum):
    ACK = "ack"
    REQUEUE = "requeue"


@dataclass(frozen=True, slots=True)
class AnalysisExecutionSettings:
    worker_id: str
    bucket: str
    lease_for: timedelta
    heartbeat_interval: float
    max_source_bytes: int
    prompt_version: str = "visual-shot.v1"
    provider: str = "controlled"
    model: str = "controlled"
    cli_version: str = "controlled"

    def __post_init__(self) -> None:
        if (
            not self.worker_id.strip()
            or not self.bucket.strip()
            or not self.prompt_version.strip()
            or not self.provider.strip()
            or not self.model.strip()
            or not self.cli_version.strip()
        ):
            raise ValueError("worker id, bucket and prompt version cannot be blank")
        if self.lease_for.total_seconds() <= 0 or self.heartbeat_interval <= 0:
            raise ValueError("lease and heartbeat interval must be positive")
        if self.heartbeat_interval >= self.lease_for.total_seconds():
            raise ValueError("heartbeat interval must be shorter than the lease")
        if self.max_source_bytes <= 0:
            raise ValueError("source byte limit must be positive")


@dataclass(frozen=True, slots=True)
class AnalysisArtifactSource:
    artifact_id: UUID
    bucket: str
    object_key: str
    sha256: str
    size_bytes: int
    duration_ms: int
    container: str


@dataclass(frozen=True, slots=True)
class LocalAnalysisArtifact:
    workspace: Path
    artifact: Path


@dataclass(frozen=True, slots=True)
class VideoAnalysisRequest:
    artifact: Path
    workspace: Path
    duration_ms: int
    size_bytes: int
    container: str
    output_language: str
    schema_version: str
    prompt_version: str

    def __post_init__(self) -> None:
        if self.duration_ms <= 0 or self.size_bytes <= 0:
            raise ValueError("video analysis media values must be positive")
        labels = (
            self.container,
            self.output_language,
            self.schema_version,
            self.prompt_version,
        )
        if any(not value.strip() for value in labels):
            raise ValueError("video analysis labels cannot be blank")
