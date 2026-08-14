"""Persistence row for one screenplay document multipart attempt."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, utc_now


class DocumentImportAttemptRow(Base):
    __tablename__ = "document_import_attempts"
    __table_args__ = (
        UniqueConstraint("object_key", name="uq_document_import_attempts_object"),
        CheckConstraint("attempt > 0", name="ck_document_import_attempts_attempt"),
        CheckConstraint(
            "status IN ("
            "'uploading','verifying','ready','failed','cancelled','expired'"
            ")",
            name="ck_document_import_attempts_status",
        ),
        CheckConstraint(
            "declared_size_bytes > 0", name="ck_document_import_attempts_declared_size"
        ),
        CheckConstraint(
            "actual_size_bytes IS NULL OR actual_size_bytes > 0",
            name="ck_document_import_attempts_actual_size",
        ),
        CheckConstraint(
            "part_size_bytes BETWEEN 5242880 AND 5368709120",
            name="ck_document_import_attempts_part_size",
        ),
        CheckConstraint(
            "part_count BETWEEN 1 AND 10000",
            name="ck_document_import_attempts_part_count",
        ),
        CheckConstraint(
            "status <> 'verifying' OR actual_size_bytes IS NOT NULL",
            name="ck_document_import_attempts_verifying_shape",
        ),
        CheckConstraint(
            "(status IN ('uploading','verifying') AND finished_at IS NULL) OR "
            "(status IN ('ready','failed','cancelled','expired') "
            "AND finished_at IS NOT NULL)",
            name="ck_document_import_attempts_terminal_shape",
        ),
        Index("ix_document_import_attempts_status_expires", "status", "expires_at"),
        Index("ix_document_import_attempts_stale", "status", "lease_expires_at"),
    )

    resource_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    attempt: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="uploading")
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    upload_id: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    declared_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actual_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    part_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    part_count: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
