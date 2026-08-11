"""Analysis worker capability heartbeats used for fail-closed admission."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, utc_now


class AnalysisWorkerHeartbeatRow(Base):
    __tablename__ = "analysis_worker_heartbeats"
    __table_args__ = (
        CheckConstraint(
            "message_schema_version > 0",
            name="ck_analysis_worker_heartbeats_schema_version",
        ),
        Index("ix_analysis_worker_heartbeats_last_seen", "last_seen_at"),
    )

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    app_version: Mapped[str] = mapped_column(String(128), nullable=False)
    message_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
