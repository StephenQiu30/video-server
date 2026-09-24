"""Durable request outcomes; independent of the lifetime of users/resources."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OperationLogRow(Base):
    __tablename__ = "operation_logs"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('started','succeeded','failed')",
            name="ck_operation_logs_outcome",
        ),
        Index("ix_operation_logs_created", "created_at", "id"),
        Index("ix_operation_logs_actor_created", "actor_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[UUID | None] = mapped_column(Uuid)
    actor_name: Mapped[str | None] = mapped_column(String(128))
    operation: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(256))
    method: Mapped[str] = mapped_column(String(8))
    route: Mapped[str] = mapped_column(String(256))
    resource_id: Mapped[UUID | None] = mapped_column(Uuid)
    resource_key: Mapped[str | None] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16), default="request")
    task_state: Mapped[str | None] = mapped_column(String(32))
    status_code: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(128))
