"""One bounded registration challenge per normalized email address."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailVerificationRow(Base):
    __tablename__ = "email_registration_challenges"
    __table_args__ = (Index("ix_email_registration_expires", "expires_at"),)

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    generation: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    code_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
