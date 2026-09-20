"""Non-secret per-route cooldown; deliberately independent of deletable jobs."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProviderRouteCooldownRow(Base):
    __tablename__ = "provider_route_cooldowns"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_provider_route_cooldown_version"),
        CheckConstraint(
            "access_policy_id IN ('public','operator_public','personal_entitled')",
            name="ck_provider_route_cooldown_policy",
        ),
        CheckConstraint(
            "(probe_owner IS NULL) = (probe_lease_until IS NULL) AND "
            "(probe_owner IS NULL OR blocked_until IS NOT NULL)",
            name="ck_provider_route_cooldown_probe",
        ),
        CheckConstraint(
            "failure_count >= 0", name="ck_provider_route_cooldown_failures"
        ),
        CheckConstraint(
            "success_streak >= 0", name="ck_provider_route_cooldown_successes"
        ),
    )

    provider_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    access_policy_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    egress_binding_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    stable_error_code: Mapped[str | None] = mapped_column(String(128))
    probe_owner: Mapped[str | None] = mapped_column(String(64))
    probe_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
