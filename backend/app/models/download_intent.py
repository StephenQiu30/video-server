"""Durable preparation state before an existing download job is created."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utc_now


class DownloadIntentRow(Base):
    __tablename__ = "download_intents"
    __table_args__ = (
        UniqueConstraint(
            "owner_hash", "idempotency_key", name="uq_download_intents_owner_key"
        ),
        UniqueConstraint("job_id", name="uq_download_intents_job"),
        CheckConstraint(
            "status IN ('queued','preparing','resolving','retry_wait',"
            "'action_required','ready','handed_off','cancelled','expired','failed')",
            name="ck_download_intents_status",
        ),
        CheckConstraint("mode = 'inspect'", name="ck_download_intents_mode"),
        CheckConstraint(
            "access_policy IN ('public','public_session',"
            "'operator_public','personal_entitled')",
            name="ck_download_intents_policy",
        ),
        CheckConstraint(
            "version >= 0 AND fence >= 0", name="ck_download_intents_version"
        ),
        CheckConstraint(
            "attempt >= 0 AND attempt <= max_attempts AND max_attempts BETWEEN 1 AND 3",
            name="ck_download_intents_attempt",
        ),
        CheckConstraint(
            "remaining_budget_ms BETWEEN 0 AND 180000",
            name="ck_download_intents_budget",
        ),
        CheckConstraint(
            "(status IN ('preparing','resolving') AND lease_owner IS NOT NULL "
            "AND lease_expires_at IS NOT NULL) OR "
            "(status NOT IN ('preparing','resolving') AND lease_owner IS NULL "
            "AND lease_expires_at IS NULL)",
            name="ck_download_intents_lease",
        ),
        CheckConstraint(
            "(status = 'retry_wait') = (retry_at IS NOT NULL)",
            name="ck_download_intents_retry",
        ),
        CheckConstraint(
            "status <> 'ready' OR inspection_id IS NOT NULL",
            name="ck_download_intents_result",
        ),
        CheckConstraint(
            "status <> 'handed_off' OR job_id IS NOT NULL",
            name="ck_download_intents_handoff",
        ),
        CheckConstraint(
            "status <> 'action_required' OR (authorization_id IS NOT NULL "
            "AND authorization_deadline IS NOT NULL)",
            name="ck_download_intents_action",
        ),
        Index("ix_download_intents_owner_created", "owner_hash", "created_at"),
        Index("ix_download_intents_recovery", "status", "lease_expires_at", "retry_at"),
        Index("ix_download_intents_deadline", "status", "deadline"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    url_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    url_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    url_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="inspect")
    access_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    remaining_budget_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=180000
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authorization_id: Mapped[UUID | None] = mapped_column(Uuid)
    authorization_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    inspection_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("media_inspections.id")
    )
    job_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("download_jobs.id"))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
