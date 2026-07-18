"""Helpers for appending the current durable Job snapshot as an event."""

from __future__ import annotations

from sqlalchemy import Connection, text

from tests.integration.persistence._resolution_aggregate import JOB_ID


def insert_current_event(connection: Connection, *, job_id: str = JOB_ID) -> None:
    connection.execute(
        text(
            """
            INSERT INTO job_events (
                job_id, owner_id, aggregate_created_at, status, stage, attempt, progress,
                error_code, error_title, error_detail, error_retryable,
                error_correlation_id, error_field, error_policy, error_actions,
                error_retry_after_seconds, occurred_at,
                detail_eligible_at, detail_must_purge_by
            )
            SELECT
                id, owner_id, created_at, status, stage, attempt, progress,
                error_code, error_title, error_detail, error_retryable,
                error_correlation_id, error_field, error_policy, error_actions,
                error_retry_after_seconds, updated_at,
                detail_eligible_at, detail_must_purge_by
            FROM jobs WHERE id = :job_id
            """
        ),
        {"job_id": job_id},
    )
