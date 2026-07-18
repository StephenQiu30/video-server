"""FastAPI Users-compatible PostgreSQL identity models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from video_server.persistence.base import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    """Application user with normalized, case-insensitive email uniqueness."""

    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at)",
            name="finite_times",
        ),
        CheckConstraint("updated_at >= created_at", name="time_order"),
    )

    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


Index("uq_users_email_normalized", func.lower(User.email), unique=True)


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    """Opaque database session token owned by one user."""

    __tablename__ = "access_tokens"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "users.id",
            name="fk_access_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
