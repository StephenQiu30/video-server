from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from uuid import UUID

from app.domain.analysis import AnalysisResult


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
    provider: str = "controlled"
    model: str = "controlled"
    cli_version: str = "controlled"

    def __post_init__(self) -> None:
        if (
            not self.worker_id.strip()
            or not self.bucket.strip()
            or not self.provider.strip()
            or not self.model.strip()
            or not self.cli_version.strip()
        ):
            raise ValueError("worker id, bucket and provider labels cannot be blank")
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
    skill_id: str
    skill_instructions: str
    custom_prompt: str | None = None

    def __post_init__(self) -> None:
        if self.duration_ms <= 0 or self.size_bytes <= 0:
            raise ValueError("video analysis media values must be positive")
        labels = (
            self.container,
            self.output_language,
            self.skill_id,
            self.skill_instructions,
        )
        if any(not value.strip() for value in labels):
            raise ValueError("video analysis labels cannot be blank")
        if self.custom_prompt is not None and (
            not self.custom_prompt.strip() or len(self.custom_prompt) > 4_000
        ):
            raise ValueError("custom prompt must be non-blank and at most 4000 chars")


@dataclass(frozen=True, slots=True)
class AnalysisExecutionOutput:
    result: AnalysisResult
    provider: str
    model: str
    cli_version: str

    def __post_init__(self) -> None:
        if any(
            not value.strip() for value in (self.provider, self.model, self.cli_version)
        ):
            raise ValueError("analysis execution provider labels cannot be blank")
