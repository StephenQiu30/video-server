"""Frozen revision-0002 columns and checks for resolution Job snapshots."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


def error_columns() -> list[sa.Column[object]]:
    """Return a fresh set of the nine frozen asynchronous-error columns."""
    return [
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_title", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("error_retryable", sa.Boolean(), nullable=True),
        sa.Column("error_correlation_id", sa.Text(), nullable=True),
        sa.Column("error_field", sa.Text(), nullable=True),
        sa.Column("error_policy", JSONB(), nullable=True),
        sa.Column("error_actions", JSONB(), nullable=True),
        sa.Column("error_retry_after_seconds", sa.Integer(), nullable=True),
    ]


def snapshot_checks(table: str) -> list[sa.CheckConstraint]:
    """Return checks shared by mutable Jobs and immutable event snapshots."""
    return [
        sa.CheckConstraint(
            "status IN ('QUEUED','RUNNING','RETRY_WAIT','SUCCEEDED','FAILED')",
            name=op.f(f"ck_{table}_status"),
        ),
        sa.CheckConstraint(
            "stage IN ('VALIDATING_URL','CHECKING_POLICY','EXTRACTING_METADATA',"
            "'NORMALIZING_FORMATS','READY')",
            name=op.f(f"ck_{table}_stage"),
        ),
        sa.CheckConstraint(
            "attempt BETWEEN 0 AND 3",
            name=op.f(f"ck_{table}_attempt"),
        ),
        sa.CheckConstraint(
            "progress IS NULL OR progress BETWEEN 0 AND 100",
            name=op.f(f"ck_{table}_progress"),
        ),
        sa.CheckConstraint(
            "(status <> 'FAILED' AND error_code IS NULL AND error_title IS NULL "
            "AND error_detail IS NULL AND error_retryable IS NULL "
            "AND error_correlation_id IS NULL AND error_field IS NULL "
            "AND error_policy IS NULL AND error_actions IS NULL "
            "AND error_retry_after_seconds IS NULL) OR "
            "(status = 'FAILED' AND error_code IS NOT NULL AND error_title IS NOT NULL "
            "AND error_detail IS NOT NULL AND error_retryable IS NOT NULL "
            "AND error_correlation_id IS NOT NULL AND btrim(error_title) <> '' "
            "AND btrim(error_detail) <> '' AND btrim(error_correlation_id) <> '')",
            name=op.f(f"ck_{table}_error"),
        ),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code IN ("
            "'INVALID_URL','UNSAFE_URL','SOURCE_UNSUPPORTED','SOURCE_POLICY_BLOCKED',"
            "'SOURCE_AUTH_REQUIRED','SOURCE_DOWNLOAD_DISABLED','SOURCE_DRM_UNSUPPORTED',"
            "'SOURCE_RATE_LIMITED','SOURCE_TIMEOUT','SOURCE_UPSTREAM_FAILED',"
            "'QUEUE_DELIVERY_FAILED','INTERNAL_ERROR')",
            name=op.f(f"ck_{table}_error_code"),
        ),
        sa.CheckConstraint(
            "r0002_safe_error_payload(error_policy, error_actions)",
            name=op.f(f"ck_{table}_error_payload"),
        ),
        sa.CheckConstraint(
            "error_retry_after_seconds IS NULL OR error_retry_after_seconds >= 0",
            name=op.f(f"ck_{table}_retry_after"),
        ),
        sa.CheckConstraint(
            "error_field IS NULL OR (char_length(error_field) BETWEEN 1 AND 128 "
            "AND error_field ~ '^(/([^~/]|~[01])*)*$' "
            "AND error_field !~ '[[:cntrl:]]')",
            name=op.f(f"ck_{table}_error_field"),
        ),
        sa.CheckConstraint(
            "(status <> 'QUEUED' OR (stage = 'VALIDATING_URL' AND attempt = 0 "
            "AND progress IS NULL)) AND "
            "(status NOT IN ('RUNNING','RETRY_WAIT','SUCCEEDED') OR attempt > 0) AND "
            "(status <> 'RETRY_WAIT' OR attempt < 3) AND "
            "(status <> 'FAILED' OR attempt > 0 OR "
            "(stage = 'VALIDATING_URL' AND progress IS NULL))",
            name=op.f(f"ck_{table}_state_shape"),
        ),
        sa.CheckConstraint(
            "(status = 'SUCCEEDED' AND stage = 'READY' AND attempt > 0 "
            "AND progress = 100 AND error_code IS NULL) OR "
            "(status <> 'SUCCEEDED' AND stage <> 'READY')",
            name=op.f(f"ck_{table}_terminal_shape"),
        ),
    ]
