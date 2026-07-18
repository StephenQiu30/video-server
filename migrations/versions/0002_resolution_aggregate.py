"""Create the source-resolution request aggregate.

Revision ID: 0002_resolution_aggregate
Revises: 0001_rights_catalog
"""

from __future__ import annotations

from alembic import op

from migrations.revision_ddl.r0002_core_tables import create_jobs, create_requests
from migrations.revision_ddl.r0002_delivery_tables import create_events, create_outbox
from migrations.revision_ddl.r0002_error_validation import (
    create_error_validation,
    drop_error_validation,
)
from migrations.revision_ddl.r0002_event_consistency import (
    create_event_consistency,
    drop_event_consistency,
)
from migrations.revision_ddl.r0002_job_guards import create_job_guards, drop_job_guards
from migrations.revision_ddl.r0002_write_guards import create_write_guards, drop_write_guards

revision = "0002_resolution_aggregate"
down_revision = "0001_rights_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_error_validation()
    create_jobs()
    create_requests()
    create_events()
    create_outbox()
    create_job_guards()
    create_write_guards()
    create_event_consistency()


def downgrade() -> None:
    drop_event_consistency()
    drop_write_guards()
    drop_job_guards()
    op.drop_table("outbox_messages")
    op.drop_table("job_events")
    op.drop_table("source_resolution_requests")
    op.drop_table("jobs")
    drop_error_validation()
