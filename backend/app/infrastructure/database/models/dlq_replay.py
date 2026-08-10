"""Audited RabbitMQ dead-letter replay facts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, utc_now


class DlqReplayRow(Base):
    __tablename__ = "rabbitmq_dlq_replays"
    __table_args__ = (
        UniqueConstraint(
            "source_queue",
            "original_event_id",
            "replay_count",
            name="uq_rabbitmq_dlq_replay_attempt",
        ),
        CheckConstraint(
            "source_queue IN ('video.download.dead','video.analysis.dead',"
            "'video.analysis-report.dead')",
            name="ck_rabbitmq_dlq_replay_queue",
        ),
        CheckConstraint(
            "status IN ('pending','published','failed')",
            name="ck_rabbitmq_dlq_replay_status",
        ),
        CheckConstraint(
            "replay_count BETWEEN 1 AND 3", name="ck_rabbitmq_dlq_replay_count"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_queue: Mapped[str] = mapped_column(String(64), nullable=False)
    original_event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    replay_event_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, unique=True)
    replay_count: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
