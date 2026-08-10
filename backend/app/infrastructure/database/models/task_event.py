"""Append-only public task projections used for realtime recovery."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..base import JSON_DOCUMENT, Base, utc_now


class TaskEventRow(Base):
    __tablename__ = "task_events"
    __table_args__ = (
        UniqueConstraint(
            "task_type", "task_id", "version", name="uq_task_events_version"
        ),
        CheckConstraint(
            "task_type IN ('download','analysis')", name="ck_task_events_type"
        ),
        CheckConstraint("version >= 0", name="ck_task_events_version"),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'", name="ck_task_events_payload_object"
        ).ddl_if(dialect="postgresql"),
        Index(
            "ix_task_events_owner_task", "owner_hash", "task_type", "task_id", "version"
        ),
        Index("ix_task_events_occurred", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(String(16), nullable=False)
    task_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    run_id: Mapped[UUID | None] = mapped_column(Uuid)
    run_no: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
