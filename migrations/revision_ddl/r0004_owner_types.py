"""Revision-0004 aggregate owner type conversions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

_OWNER_TABLES = (
    "jobs",
    "source_resolution_requests",
    "job_events",
    "outbox_messages",
)


def alter_owner_columns_to_uuid() -> None:
    for table in _OWNER_TABLES:
        op.alter_column(
            table,
            "owner_id",
            existing_type=sa.Text(),
            type_=postgresql.UUID(as_uuid=True),
            existing_nullable=False,
            postgresql_using="owner_id::uuid",
        )


def alter_owner_columns_to_text() -> None:
    for table in reversed(_OWNER_TABLES):
        op.alter_column(
            table,
            "owner_id",
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.Text(),
            existing_nullable=False,
            postgresql_using="owner_id::text",
        )
