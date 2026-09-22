"""Independent guest material and bounded preparation ownership."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProviderGuestContextRow(Base):
    __tablename__ = "provider_guest_contexts"
    __table_args__ = (
        UniqueConstraint(
            "provider_key",
            "profile_version",
            "client_profile_id",
            "egress_affinity_id",
            name="uq_guest_context_scope",
        ),
        CheckConstraint(
            "state IN ('absent','preparing','ready','refreshing',"
            "'cooling','expired','revoked')",
            name="ck_guest_context_state",
        ),
        CheckConstraint(
            "revision >= 0 AND fence >= 0 AND failures >= 0",
            name="ck_guest_context_counters",
        ),
        CheckConstraint(
            "(ciphertext IS NULL) = (valid_until IS NULL) AND "
            "(ciphertext IS NULL) = (refresh_after IS NULL)",
            name="ck_guest_context_material",
        ),
        CheckConstraint(
            "state <> 'ready' OR ciphertext IS NOT NULL", name="ck_guest_context_ready"
        ),
        CheckConstraint(
            "state <> 'revoked' OR ciphertext IS NULL",
            name="ck_guest_context_revocation",
        ),
        CheckConstraint(
            "(state IN ('preparing','refreshing') AND lease_owner IS NOT NULL "
            "AND lease_expires_at IS NOT NULL) OR "
            "(state NOT IN ('preparing','refreshing') AND lease_owner IS NULL "
            "AND lease_expires_at IS NULL)",
            name="ck_guest_context_lease",
        ),
        CheckConstraint(
            "(state = 'cooling') = (retry_at IS NOT NULL)",
            name="ck_guest_context_retry",
        ),
        Index("ix_guest_context_maintenance", "state", "lease_expires_at", "retry_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_key: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_version: Mapped[str] = mapped_column(String(128), nullable=False)
    client_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    egress_affinity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="absent")
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    fence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
