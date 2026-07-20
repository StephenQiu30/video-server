"""Public download job and artifact DTOs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _read(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


class CreateDownloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    format_id: UUID
    client_request_id: UUID


class JobError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ArtifactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    file_name: str
    content_type: str
    size_bytes: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    expires_at: datetime

    @field_serializer("expires_at", when_used="json")
    def serialize_expires_at(self, value: datetime) -> str:
        return _utc(value).isoformat().replace("+00:00", "Z")

    @classmethod
    def from_model(cls, value: Any) -> ArtifactSummary:
        if isinstance(value, cls):
            return value
        return cls(
            file_name=_read(value, "file_name"),
            content_type=_read(value, "content_type"),
            size_bytes=_read(value, "size_bytes"),
            sha256=_read(value, "sha256"),
            expires_at=_read(value, "expires_at"),
        )


class DownloadJob(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    status: Literal["queued", "running", "succeeded", "failed", "expired"]
    stage: Literal["downloading", "merging", "verifying", "uploading"] | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    downloaded_bytes: int | None = Field(default=None, ge=0)
    total_bytes: int | None = Field(default=None, ge=0)
    error: JobError | None = None
    artifact: ArtifactSummary | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime) -> str:
        return _utc(value).isoformat().replace("+00:00", "Z")

    @classmethod
    def from_model(cls, value: Any) -> DownloadJob:
        if isinstance(value, cls):
            return value
        error_code = _read(value, "error_code")
        error_message = _read(value, "error_message")
        error = (
            JobError(code=error_code, message=error_message)
            if error_code and error_message
            else None
        )
        artifact_value = _read(value, "artifact")
        artifact = (
            ArtifactSummary.from_model(artifact_value)
            if artifact_value is not None
            else None
        )
        return cls(
            id=_read(value, "id"),
            status=_read(value, "status"),
            stage=_read(value, "stage"),
            progress_percent=_read(value, "progress_percent"),
            downloaded_bytes=_read(value, "downloaded_bytes"),
            total_bytes=_read(value, "total_bytes"),
            error=error,
            artifact=artifact,
            created_at=_read(value, "created_at"),
            updated_at=_read(value, "updated_at"),
        )


class DownloadUrl(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    expires_at: datetime
    file_name: str

    @field_serializer("expires_at", when_used="json")
    def serialize_expires_at(self, value: datetime) -> str:
        return _utc(value).isoformat().replace("+00:00", "Z")


__all__ = [
    "ArtifactSummary",
    "CreateDownloadRequest",
    "DownloadJob",
    "DownloadUrl",
    "JobError",
]
