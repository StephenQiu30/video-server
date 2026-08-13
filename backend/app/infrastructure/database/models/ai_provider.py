"""AI analysis Provider profiles."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    LargeBinary,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, utc_now


class AiProviderProfileRow(Base):
    __tablename__ = "ai_provider_profiles"
    __table_args__ = (
        CheckConstraint("engine IN ('codex', 'claude')", name="ck_ai_provider_engine"),
        CheckConstraint(
            "auth_mode IN ('host_login', 'api_key')",
            name="ck_ai_provider_auth_mode",
        ),
        CheckConstraint(
            "(auth_mode = 'host_login' AND base_url IS NULL "
            "AND credential_ciphertext IS NULL AND credential_key_id IS NULL) OR "
            "(auth_mode = 'api_key' AND base_url IS NOT NULL "
            "AND credential_ciphertext IS NOT NULL AND credential_key_id IS NOT NULL)",
            name="ck_ai_provider_auth_shape",
        ),
        Index(
            "uq_ai_provider_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    engine: Mapped[str] = mapped_column(String(16), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(2048))
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    credential_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    credential_key_id: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
