"""Deployment-owned encrypted sources; local Runner files are disposable replicas."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProviderSessionSourceRow(Base):
    __tablename__ = "provider_session_sources"
    __table_args__ = (
        CheckConstraint("revision > 0", name="ck_provider_source_revision"),
        CheckConstraint(
            "(ciphertext IS NULL) = (valid_until IS NULL)",
            name="ck_provider_source_revocation",
        ),
    )

    provider_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
