"""Durable administrator source-maintenance transactions, not content grants."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProviderAuthorizationRow(Base):
    __tablename__ = "provider_authorizations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','source_available','authorization_required',"
            "'permission_required','expired','cancelled','failed')",
            name="ck_provider_authorizations_status",
        ),
        CheckConstraint(
            "source IN ('current_chrome','dedicated_chrome')",
            name="ck_provider_authorizations_source",
        ),
        CheckConstraint(
            "purpose = 'maintain_deployment_source'",
            name="ck_provider_authorizations_purpose",
        ),
        CheckConstraint(
            "expires_at > created_at AND retain_until >= expires_at",
            name="ck_provider_authorizations_deadline",
        ),
        Index(
            "uq_provider_authorizations_active",
            "provider_key",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_provider_authorizations_retention", "retain_until"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    retain_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
