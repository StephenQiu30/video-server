"""SQLAlchemy models for persisted download jobs and MinIO artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.media.models import utcnow

if TYPE_CHECKING:
    from src.media.models import MediaFormat, MediaSource


class DownloadJob(Base):
    __tablename__ = "download_jobs"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_download_jobs_source"),
        UniqueConstraint(
            "owner_token_hash",
            "client_request_id",
            name="uq_download_jobs_owner_request",
        ),
        ForeignKeyConstraint(
            ["owner_token_hash", "source_id"],
            ["media_sources.owner_token_hash", "media_sources.id"],
            name="fk_download_jobs_source_owner",
        ),
        ForeignKeyConstraint(
            ["source_id", "format_id"],
            ["media_formats.source_id", "media_formats.id"],
            name="fk_download_jobs_format_source",
        ),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','expired')",
            name="ck_download_jobs_status",
        ),
        CheckConstraint(
            "stage IS NULL OR stage IN ("
            "'downloading','merging','verifying','uploading')",
            name="ck_download_jobs_stage",
        ),
        CheckConstraint(
            "progress_percent IS NULL OR progress_percent BETWEEN 0 AND 100",
            name="ck_download_jobs_progress",
        ),
        CheckConstraint(
            "downloaded_bytes IS NULL OR downloaded_bytes >= 0",
            name="ck_download_jobs_downloaded_bytes",
        ),
        CheckConstraint(
            "total_bytes IS NULL OR total_bytes >= 0",
            name="ck_download_jobs_total_bytes",
        ),
        CheckConstraint("version >= 0", name="ck_download_jobs_version"),
        Index("ix_download_jobs_status_published", "status", "published_at"),
        Index("ix_download_jobs_format_id", "format_id"),
        Index("ix_download_jobs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    client_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    format_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    stage: Mapped[str | None] = mapped_column(String(20))
    progress_percent: Mapped[int | None] = mapped_column(SmallInteger)
    downloaded_bytes: Mapped[int | None] = mapped_column(BigInteger)
    total_bytes: Mapped[int | None] = mapped_column(BigInteger)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    source: Mapped[MediaSource] = relationship(
        back_populates="download_job",
        foreign_keys=[source_id],
        overlaps="format,download_jobs",
    )
    format: Mapped[MediaFormat] = relationship(
        back_populates="download_jobs", foreign_keys=[format_id], overlaps="source"
    )
    artifact: Mapped[Artifact | None] = relationship(
        back_populates="download_job",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_artifacts_size"),
        Index("ix_artifacts_expires_at", "expires_at"),
        Index("ix_artifacts_deleted_at", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    download_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("download_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    download_job: Mapped[DownloadJob] = relationship(back_populates="artifact")
