"""Frozen revision-0002 event and outbox tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from migrations.revision_ddl.r0002_columns import error_columns, snapshot_checks


def create_events() -> None:
    op.create_table(
        "job_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("aggregate_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("attempt", sa.SmallInteger(), nullable=False),
        sa.Column("progress", sa.SmallInteger(), nullable=True),
        *error_columns(),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_must_purge_by", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "id > 0",
            name=op.f("ck_job_events_id_positive"),
        ),
        sa.CheckConstraint(
            "isfinite(aggregate_created_at) AND isfinite(occurred_at) "
            "AND isfinite(detail_eligible_at) AND isfinite(detail_must_purge_by)",
            name=op.f("ck_job_events_finite_times"),
        ),
        sa.CheckConstraint(
            "occurred_at >= aggregate_created_at",
            name=op.f("ck_job_events_occurred_at"),
        ),
        sa.CheckConstraint(
            "detail_eligible_at = aggregate_created_at + interval '166 hours' "
            "AND detail_must_purge_by = aggregate_created_at + interval '168 hours'",
            name=op.f("ck_job_events_retention"),
        ),
        *snapshot_checks("job_events"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_events")),
        sa.UniqueConstraint(
            "job_id",
            "occurred_at",
            name=op.f("uq_job_events_job_snapshot"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id", "owner_id", "aggregate_created_at"],
            ["jobs.id", "jobs.owner_id", "jobs.created_at"],
            name=op.f("fk_job_events_job_identity"),
        ),
    )
    op.create_index(
        op.f("ix_job_events_job_id_id"),
        "job_events",
        ["job_id", "id"],
        unique=False,
    )


def create_outbox() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("resolution_request_id", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("aggregate_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("claimed_by", sa.Text(), nullable=True),
        sa.Column("claim_token", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("lease_version", sa.BigInteger(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_error_code", sa.Text(), nullable=True),
        sa.Column("retention_eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retention_must_purge_by", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "id > 0",
            name=op.f("ck_outbox_messages_id_positive"),
        ),
        sa.CheckConstraint(
            "kind = 'SOURCE_RESOLUTION_REQUESTED'",
            name=op.f("ck_outbox_messages_kind"),
        ),
        sa.CheckConstraint(
            "attempts BETWEEN 0 AND 10 AND lease_version = attempts",
            name=op.f("ck_outbox_messages_attempts"),
        ),
        sa.CheckConstraint(
            "(claimed_by IS NULL AND claim_token IS NULL AND claimed_at IS NULL "
            "AND lease_expires_at IS NULL) OR "
            "(claimed_by IS NOT NULL AND claim_token IS NOT NULL AND claimed_at IS NOT NULL "
            "AND lease_expires_at > claimed_at)",
            name=op.f("ck_outbox_messages_lease"),
        ),
        sa.CheckConstraint(
            "(attempts > 0 OR (claimed_by IS NULL AND claim_token IS NULL "
            "AND next_attempt_at IS NULL AND published_at IS NULL "
            "AND dead_lettered_at IS NULL)) AND "
            "(claimed_by IS NULL OR (btrim(claimed_by) <> '' "
            "AND btrim(claim_token) <> '' AND attempts > 0)) AND "
            "(next_attempt_at IS NULL OR (attempts > 0 AND claimed_by IS NULL "
            "AND published_at IS NULL AND dead_lettered_at IS NULL)) AND "
            "(published_at IS NULL OR (attempts > 0 AND claimed_by IS NULL "
            "AND next_attempt_at IS NULL)) AND "
            "(dead_lettered_at IS NULL OR (claimed_by IS NULL "
            "AND next_attempt_at IS NULL))",
            name=op.f("ck_outbox_messages_lifecycle"),
        ),
        sa.CheckConstraint(
            "NOT (published_at IS NOT NULL AND dead_lettered_at IS NOT NULL) "
            "AND (dead_lettered_at IS NULL OR "
            "(attempts = 10 AND terminal_error_code = 'QUEUE_DELIVERY_FAILED')) "
            "AND (dead_lettered_at IS NOT NULL OR terminal_error_code IS NULL)",
            name=op.f("ck_outbox_messages_terminal"),
        ),
        sa.CheckConstraint(
            "(published_at IS NULL AND "
            "retention_eligible_at = aggregate_created_at + interval '166 hours' AND "
            "retention_must_purge_by = aggregate_created_at + interval '168 hours') OR "
            "(published_at IS NOT NULL AND "
            "retention_eligible_at = published_at + interval '22 hours' AND "
            "retention_must_purge_by = published_at + interval '24 hours')",
            name=op.f("ck_outbox_messages_retention"),
        ),
        sa.CheckConstraint(
            "retention_eligible_at < retention_must_purge_by",
            name=op.f("ck_outbox_messages_retention_order"),
        ),
        sa.CheckConstraint(
            "isfinite(aggregate_created_at) AND isfinite(retention_eligible_at) "
            "AND isfinite(retention_must_purge_by) "
            "AND (claimed_at IS NULL OR isfinite(claimed_at)) "
            "AND (lease_expires_at IS NULL OR isfinite(lease_expires_at)) "
            "AND (next_attempt_at IS NULL OR isfinite(next_attempt_at)) "
            "AND (published_at IS NULL OR isfinite(published_at)) "
            "AND (dead_lettered_at IS NULL OR isfinite(dead_lettered_at))",
            name=op.f("ck_outbox_messages_finite_times"),
        ),
        sa.CheckConstraint(
            "(claimed_at IS NULL OR claimed_at >= aggregate_created_at) AND "
            "(next_attempt_at IS NULL OR next_attempt_at >= aggregate_created_at) AND "
            "(published_at IS NULL OR published_at >= aggregate_created_at) AND "
            "(dead_lettered_at IS NULL OR dead_lettered_at >= aggregate_created_at)",
            name=op.f("ck_outbox_messages_time_order"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_messages")),
        sa.UniqueConstraint("job_id", "kind", name=op.f("uq_outbox_messages_job_kind")),
        sa.ForeignKeyConstraint(
            ["resolution_request_id", "job_id", "owner_id", "aggregate_created_at"],
            [
                "source_resolution_requests.id",
                "source_resolution_requests.job_id",
                "source_resolution_requests.owner_id",
                "source_resolution_requests.created_at",
            ],
            name=op.f("fk_outbox_messages_resolution_identity"),
        ),
    )
    op.create_index(
        op.f("ix_outbox_messages_dispatch"),
        "outbox_messages",
        ["next_attempt_at", "lease_expires_at", "id"],
        unique=False,
        postgresql_where=sa.text("published_at IS NULL AND dead_lettered_at IS NULL"),
    )
