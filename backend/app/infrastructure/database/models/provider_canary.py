"""Append-only Provider canary evidence without target URLs or credentials."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, utc_now


class ProviderCanaryResultRow(Base):
    __tablename__ = "provider_canary_results"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('metadata','media','analysis')",
            name="ck_provider_canary_stage",
        ),
        CheckConstraint(
            "access_mode IN ('anonymous','operator_managed')",
            name="ck_provider_canary_access_mode",
        ),
        CheckConstraint(
            "outcome IN ('succeeded','failed')", name="ck_provider_canary_outcome"
        ),
        CheckConstraint("duration_ms >= 0", name="ck_provider_canary_duration"),
        CheckConstraint(
            "(outcome = 'failed') = (stable_error_code IS NOT NULL)",
            name="ck_provider_canary_error",
        ),
        Index(
            "ix_provider_canary_provider_checked",
            "provider_key",
            "checked_at",
        ),
        Index("ix_provider_canary_target_checked", "target_id", "stage", "checked_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    access_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    stable_error_code: Mapped[str | None] = mapped_column(String(128))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_commit: Mapped[str] = mapped_column(String(128), nullable=False)
    egress_affinity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    client_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
