"""Frozen revision-0002 core tables for the resolution aggregate."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from migrations.revision_ddl.r0002_columns import error_columns, snapshot_checks


def create_jobs() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("attempt", sa.SmallInteger(), nullable=False),
        sa.Column("progress", sa.SmallInteger(), nullable=True),
        *error_columns(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detail_eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_must_purge_by", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            r"id ~ '^job_[A-Za-z0-9_-]+$' AND octet_length(id) <= 128",
            name=op.f("ck_jobs_id_format"),
        ),
        sa.CheckConstraint(
            r"owner_id ~ '^[A-Za-z0-9_-]+$' AND octet_length(owner_id) <= 128",
            name=op.f("ck_jobs_owner_format"),
        ),
        sa.CheckConstraint(
            "job_type = 'SOURCE_RESOLUTION'",
            name=op.f("ck_jobs_type"),
        ),
        sa.CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND (terminal_at IS NULL OR isfinite(terminal_at)) "
            "AND isfinite(detail_eligible_at) AND isfinite(detail_must_purge_by)",
            name=op.f("ck_jobs_finite_times"),
        ),
        sa.CheckConstraint(
            "detail_eligible_at = created_at + interval '166 hours' "
            "AND detail_must_purge_by = created_at + interval '168 hours'",
            name=op.f("ck_jobs_retention"),
        ),
        sa.CheckConstraint(
            "updated_at >= created_at AND (terminal_at IS NULL OR terminal_at >= created_at)",
            name=op.f("ck_jobs_time_order"),
        ),
        sa.CheckConstraint(
            "(status IN ('SUCCEEDED','FAILED')) = (terminal_at IS NOT NULL)",
            name=op.f("ck_jobs_terminal_time"),
        ),
        *snapshot_checks("jobs"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint(
            "id", "owner_id", "created_at", name=op.f("uq_jobs_aggregate_identity")
        ),
    )


def create_requests() -> None:
    op.create_table(
        "source_resolution_requests",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("idempotency_key_digest", sa.CHAR(64), nullable=False),
        sa.Column("request_digest", sa.CHAR(64), nullable=False),
        sa.Column("url_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("url_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("url_wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("url_wrap_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("url_key_id", sa.Text(), nullable=False),
        sa.Column("rights_statement_version", sa.Text(), nullable=False),
        sa.Column("rights_statement_locale", sa.Text(), nullable=False),
        sa.Column("rights_statement_sha256", sa.CHAR(64), nullable=False),
        sa.Column("rights_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_must_purge_by", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            r"id ~ '^res_[A-Za-z0-9_-]+$' AND octet_length(id) <= 128",
            name=op.f("ck_source_resolution_requests_id_format"),
        ),
        sa.CheckConstraint(
            r"owner_id ~ '^[A-Za-z0-9_-]+$' AND octet_length(owner_id) <= 128",
            name=op.f("ck_source_resolution_requests_owner_format"),
        ),
        sa.CheckConstraint(
            "operation = 'probe'", name=op.f("ck_source_resolution_requests_operation")
        ),
        sa.CheckConstraint(
            r"idempotency_key_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_source_resolution_requests_key_digest"),
        ),
        sa.CheckConstraint(
            r"request_digest ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_source_resolution_requests_request_digest"),
        ),
        sa.CheckConstraint(
            "octet_length(url_ciphertext) > 16",
            name=op.f("ck_source_resolution_requests_ciphertext"),
        ),
        sa.CheckConstraint(
            "octet_length(url_nonce) = 24",
            name=op.f("ck_source_resolution_requests_nonce"),
        ),
        sa.CheckConstraint(
            "octet_length(url_wrapped_dek) = 48",
            name=op.f("ck_source_resolution_requests_wrapped_dek"),
        ),
        sa.CheckConstraint(
            "octet_length(url_wrap_nonce) = 24",
            name=op.f("ck_source_resolution_requests_wrap_nonce"),
        ),
        sa.CheckConstraint(
            r"url_key_id ~ '^[A-Za-z0-9_-]+$' AND octet_length(url_key_id) <= 128",
            name=op.f("ck_source_resolution_requests_key_id"),
        ),
        sa.CheckConstraint(
            "isfinite(rights_confirmed_at) AND isfinite(created_at) "
            "AND isfinite(detail_eligible_at) AND isfinite(detail_must_purge_by)",
            name=op.f("ck_source_resolution_requests_finite_times"),
        ),
        sa.CheckConstraint(
            "detail_eligible_at = created_at + interval '166 hours' "
            "AND detail_must_purge_by = created_at + interval '168 hours'",
            name=op.f("ck_source_resolution_requests_retention"),
        ),
        sa.CheckConstraint(
            "rights_confirmed_at <= created_at",
            name=op.f("ck_source_resolution_requests_rights_time"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_resolution_requests")),
        sa.UniqueConstraint(
            "owner_id",
            "operation",
            "idempotency_key_digest",
            name=op.f("uq_source_resolution_requests_idempotency_scope"),
        ),
        sa.UniqueConstraint("job_id", name=op.f("uq_source_resolution_requests_job_id")),
        sa.UniqueConstraint(
            "id",
            "job_id",
            "owner_id",
            "created_at",
            name=op.f("uq_source_resolution_requests_aggregate_identity"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id", "owner_id", "created_at"],
            ["jobs.id", "jobs.owner_id", "jobs.created_at"],
            name=op.f("fk_source_resolution_requests_job_identity"),
        ),
        sa.ForeignKeyConstraint(
            [
                "rights_statement_version",
                "rights_statement_locale",
                "rights_statement_sha256",
            ],
            [
                "rights_statement_catalog.version",
                "rights_statement_catalog.locale",
                "rights_statement_catalog.statement_sha256",
            ],
            name=op.f("fk_source_resolution_requests_rights"),
        ),
    )
