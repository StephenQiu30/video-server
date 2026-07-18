"""Revision-0004 constraints around aggregate owner types."""

from __future__ import annotations

from alembic import op


def drop_text_owner_dependencies() -> None:
    _drop_aggregate_foreign_keys()
    _drop_owner_unique_constraints()
    op.drop_constraint(
        op.f("ck_source_resolution_requests_owner_format"),
        "source_resolution_requests",
        type_="check",
    )
    op.drop_constraint(op.f("ck_jobs_owner_format"), "jobs", type_="check")


def create_uuid_owner_dependencies() -> None:
    _create_owner_unique_constraints()
    _create_aggregate_foreign_keys()
    for table in (
        "jobs",
        "source_resolution_requests",
        "job_events",
        "outbox_messages",
    ):
        op.create_foreign_key(
            op.f(f"fk_{table}_owner_id_users"),
            table,
            "users",
            ["owner_id"],
            ["id"],
        )


def drop_uuid_owner_dependencies() -> None:
    for table in (
        "outbox_messages",
        "job_events",
        "source_resolution_requests",
        "jobs",
    ):
        op.drop_constraint(
            op.f(f"fk_{table}_owner_id_users"),
            table,
            type_="foreignkey",
        )
    _drop_aggregate_foreign_keys()
    _drop_owner_unique_constraints()


def create_text_owner_dependencies() -> None:
    owner_format = r"owner_id ~ '^[A-Za-z0-9_-]+$' AND octet_length(owner_id) <= 128"
    op.create_check_constraint(
        op.f("ck_jobs_owner_format"),
        "jobs",
        owner_format,
    )
    op.create_check_constraint(
        op.f("ck_source_resolution_requests_owner_format"),
        "source_resolution_requests",
        owner_format,
    )
    _create_owner_unique_constraints()
    _create_aggregate_foreign_keys()


def _drop_aggregate_foreign_keys() -> None:
    op.drop_constraint(
        op.f("fk_outbox_messages_resolution_identity"),
        "outbox_messages",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_job_events_job_identity"),
        "job_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_source_resolution_requests_job_identity"),
        "source_resolution_requests",
        type_="foreignkey",
    )


def _drop_owner_unique_constraints() -> None:
    op.drop_constraint(
        op.f("uq_source_resolution_requests_aggregate_identity"),
        "source_resolution_requests",
        type_="unique",
    )
    op.drop_constraint(
        op.f("uq_source_resolution_requests_idempotency_scope"),
        "source_resolution_requests",
        type_="unique",
    )
    op.drop_constraint(
        op.f("uq_jobs_aggregate_identity"),
        "jobs",
        type_="unique",
    )


def _create_owner_unique_constraints() -> None:
    op.create_unique_constraint(
        op.f("uq_jobs_aggregate_identity"),
        "jobs",
        ["id", "owner_id", "created_at"],
    )
    op.create_unique_constraint(
        op.f("uq_source_resolution_requests_idempotency_scope"),
        "source_resolution_requests",
        ["owner_id", "operation", "idempotency_key_digest"],
    )
    op.create_unique_constraint(
        op.f("uq_source_resolution_requests_aggregate_identity"),
        "source_resolution_requests",
        ["id", "job_id", "owner_id", "created_at"],
    )


def _create_aggregate_foreign_keys() -> None:
    op.create_foreign_key(
        op.f("fk_source_resolution_requests_job_identity"),
        "source_resolution_requests",
        "jobs",
        ["job_id", "owner_id", "created_at"],
        ["id", "owner_id", "created_at"],
    )
    op.create_foreign_key(
        op.f("fk_job_events_job_identity"),
        "job_events",
        "jobs",
        ["job_id", "owner_id", "aggregate_created_at"],
        ["id", "owner_id", "created_at"],
    )
    op.create_foreign_key(
        op.f("fk_outbox_messages_resolution_identity"),
        "outbox_messages",
        "source_resolution_requests",
        ["resolution_request_id", "job_id", "owner_id", "aggregate_created_at"],
        ["id", "job_id", "owner_id", "created_at"],
    )
