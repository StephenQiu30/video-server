from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.analysis import (
    AnalysisErrorCode,
    AnalysisResult,
    AnalysisStage,
    AnalysisStatus,
)


@dataclass(frozen=True, slots=True)
class AnalysisArtifactSnapshot:
    id: UUID
    download_id: UUID
    owner_hash: str
    download_status: str
    sha256: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisCreate:
    id: UUID
    artifact_id: UUID
    owner_hash: str
    idempotency_key: str
    request_fingerprint: str
    input_sha256: str
    skill_id: str
    skill_instructions: str
    output_language: str
    custom_prompt: str | None
    max_attempts: int
    outbox_event_id: UUID
    outbox_event_type: str


@dataclass(frozen=True, slots=True)
class AnalysisJobSnapshot:
    id: UUID
    artifact_id: UUID
    owner_hash: str
    request_fingerprint: str
    input_sha256: str
    skill_id: str
    skill_instructions: str
    output_language: str
    custom_prompt: str | None
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

    @classmethod
    def queued(cls, command: AnalysisCreate, *, now: datetime) -> AnalysisJobSnapshot:
        return cls(
            id=command.id,
            artifact_id=command.artifact_id,
            owner_hash=command.owner_hash,
            request_fingerprint=command.request_fingerprint,
            input_sha256=command.input_sha256,
            skill_id=command.skill_id,
            skill_instructions=command.skill_instructions,
            output_language=command.output_language,
            custom_prompt=command.custom_prompt,
            status=AnalysisStatus.QUEUED.value,
            stage=None,
            progress=0,
            attempt=0,
            max_attempts=command.max_attempts,
            version=0,
            lease_owner=None,
            lease_expires_at=None,
            heartbeat_at=None,
            started_at=None,
            retry_at=None,
            finished_at=None,
            error_code=None,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True, slots=True)
class AnalysisJobSaveResult:
    job: AnalysisJobSnapshot
    created: bool


@dataclass(frozen=True, slots=True)
class AnalysisPublish:
    job_id: UUID
    result: AnalysisResult
    lease_owner: str
    expected_version: int
    provider: str
    model: str
    cli_version: str
    now: datetime


@dataclass(frozen=True, slots=True)
class AnalysisJobView:
    id: UUID
    skill_id: str
    output_language: str
    status: AnalysisStatus
    stage: AnalysisStage | None
    progress: int
    attempt: int
    error_code: AnalysisErrorCode | None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None
    result: AnalysisResult | None


@dataclass(frozen=True, slots=True)
class AnalysisReportFile:
    content: bytes
    filename: str
    media_type: str


@dataclass(frozen=True, slots=True)
class AnalysisSkillView:
    id: str
    display_name: str
    description: str
    default_prompt: str
