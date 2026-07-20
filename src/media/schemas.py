"""Public media inspection DTOs.

These models intentionally contain only normalized display fields.  Provider
format IDs and source URLs remain server-side implementation details.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
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


class InspectMediaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)


class MediaFormat(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    label: str
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    container: str
    video_codec: str
    audio_codec: str
    estimated_size_bytes: int | None = None
    requires_merge: bool

    @classmethod
    def from_model(cls, value: Any) -> MediaFormat:
        fps = _read(value, "fps")
        if isinstance(fps, Decimal):
            fps = float(fps)
        if isinstance(value, cls):
            return value
        return cls(
            id=_read(value, "id"),
            label=_read(value, "label"),
            width=_read(value, "width"),
            height=_read(value, "height"),
            fps=fps,
            container=_read(value, "container"),
            video_codec=_read(value, "video_codec"),
            audio_codec=_read(value, "audio_codec"),
            estimated_size_bytes=_read(value, "estimated_size_bytes"),
            requires_merge=_read(value, "requires_merge"),
        )


class InspectedMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    title: str
    platform: str
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    expires_at: datetime
    formats: list[MediaFormat]

    @field_serializer("expires_at", when_used="json")
    def serialize_expires_at(self, value: datetime) -> str:
        return _utc(value).isoformat().replace("+00:00", "Z")

    @classmethod
    def from_model(cls, value: Any) -> InspectedMedia:
        if isinstance(value, cls):
            return value
        formats = [MediaFormat.from_model(item) for item in _read(value, "formats", [])]
        platform = _read(value, "platform") or _read(value, "extractor_key", "")
        expires_at = _read(value, "expires_at") or _read(value, "inspect_expires_at")
        if expires_at is None:
            raise ValueError("inspected media is missing expires_at")
        return cls(
            id=_read(value, "id"),
            title=_read(value, "title"),
            platform=platform,
            thumbnail_url=_read(value, "thumbnail_url"),
            duration_seconds=_read(value, "duration_seconds"),
            expires_at=expires_at,
            formats=formats,
        )


__all__ = ["InspectMediaRequest", "InspectedMedia", "MediaFormat"]
