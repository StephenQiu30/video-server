"""Persistence rows for independent AI analysis jobs and strict results."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
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

from ..base import JSON_DOCUMENT, Base, utc_now


class AnalysisJobRow(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        UniqueConstraint(
            "owner_hash",
            "idempotency_key",
            name="uq_analysis_jobs_owner_idempotency",
        ),
        CheckConstraint(
            "status IN ("
            "'queued','running','retry_wait','succeeded','failed','cancelled'"
            ")",
            name="ck_analysis_jobs_status",
        ),
        CheckConstraint("progress BETWEEN 0 AND 100", name="ck_analysis_jobs_progress"),
        CheckConstraint("attempt >= 0", name="ck_analysis_jobs_attempt"),
        CheckConstraint("max_attempts > 0", name="ck_analysis_jobs_max_attempts"),
        CheckConstraint("version >= 0", name="ck_analysis_jobs_version"),
        CheckConstraint(
            "stage_rank BETWEEN 0 AND 3", name="ck_analysis_jobs_stage_rank"
        ),
        CheckConstraint(
            "length(input_sha256) = 64", name="ck_analysis_jobs_sha256_length"
        ),
        Index("ix_analysis_jobs_owner_created", "owner_hash", "created_at"),
        Index("ix_analysis_jobs_claim", "status", "retry_at"),
        Index("ix_analysis_jobs_stale", "status", "lease_expires_at"),
        Index("ix_analysis_jobs_artifact", "artifact_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    artifact_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    owner_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    output_language: Mapped[str] = mapped_column(String(35), nullable=False)
    custom_prompt: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    stage: Mapped[str | None] = mapped_column(String(24))
    stage_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class AnalysisResultRow(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_analysis_results_job"),
        CheckConstraint(
            "length(input_sha256) = 64", name="ck_analysis_results_sha256_length"
        ),
        CheckConstraint(
            "jsonb_typeof(result_json) = 'object'",
            name="ck_analysis_results_json_object",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(35), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    cli_version: Mapped[str] = mapped_column(String(128), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AnalysisArtifactLockRow(Base):
    __tablename__ = "analysis_artifact_locks"
    __table_args__ = (Index("ix_analysis_artifact_locks_artifact", "artifact_id"),)

    job_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
