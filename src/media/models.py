"""SQLAlchemy models for inspected media sources and their formats."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.downloads.models import DownloadJob


def utcnow() -> datetime:
    return datetime.now(UTC)


class MediaSource(Base):
    __tablename__ = "media_sources"
    __table_args__ = (
        UniqueConstraint("owner_token_hash", "id", name="uq_media_sources_owner_id"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_media_sources_duration",
        ),
        Index(
            "ix_media_sources_owner_inspect_expires",
            "owner_token_hash",
            "inspect_expires_at",
        ),
        Index("ix_media_sources_inspect_expires", "inspect_expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_host: Mapped[str] = mapped_column(String(253), nullable=False)
    extractor_key: Mapped[str] = mapped_column(String(100), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    inspect_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    formats: Mapped[list[MediaFormat]] = relationship(
        back_populates="source", cascade="all, delete-orphan", passive_deletes=True
    )
    download_job: Mapped[DownloadJob | None] = relationship(
        back_populates="source", uselist=False
    )


class MediaFormat(Base):
    __tablename__ = "media_formats"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "sort_order", name="uq_media_formats_source_sort"
        ),
        UniqueConstraint("source_id", "id", name="uq_media_formats_source_id"),
        CheckConstraint("width IS NULL OR width > 0", name="ck_media_formats_width"),
        CheckConstraint("height IS NULL OR height > 0", name="ck_media_formats_height"),
        CheckConstraint("fps IS NULL OR fps > 0", name="ck_media_formats_fps"),
        CheckConstraint(
            "estimated_size_bytes IS NULL OR estimated_size_bytes >= 0",
            name="ck_media_formats_size",
        ),
        CheckConstraint("sort_order >= 0", name="ck_media_formats_sort"),
        Index("ix_media_formats_source_id", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("media_sources.id", ondelete="CASCADE"), nullable=False
    )
    video_format_id: Mapped[str] = mapped_column(String(100), nullable=False)
    audio_format_id: Mapped[str | None] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Numeric(6, 2))
    container: Mapped[str] = mapped_column(String(20), nullable=False)
    video_codec: Mapped[str] = mapped_column(String(100), nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    requires_merge: Mapped[bool] = mapped_column(nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    source: Mapped[MediaSource] = relationship(back_populates="formats")
    download_jobs: Mapped[list[DownloadJob]] = relationship(
        back_populates="format", overlaps="download_job,source"
    )
