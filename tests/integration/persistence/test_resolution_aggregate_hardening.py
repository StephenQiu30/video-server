"""Adversarial database guards for resolution aggregate snapshots."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._resolution_aggregate import (
    NOW,
    insert_aggregate,
    insert_event,
    insert_job,
    insert_request,
    seed_rights,
)
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration


def test_failed_job_requires_the_complete_safe_error(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            connection.execute(
                text(
                    """
                    UPDATE jobs
                    SET status='FAILED', terminal_at=:at, updated_at=:at
                    """
                ),
                {"at": NOW + timedelta(seconds=1)},
            )
    assert_constraint(rejected.value, name="ck_jobs_error")


def test_event_rejects_exhausted_retry_wait(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            insert_event(
                connection,
                status="RETRY_WAIT",
                stage="CHECKING_POLICY",
                attempt=3,
                occurred_at=NOW + timedelta(seconds=1),
            )
    assert getattr(rejected.value.orig, "sqlstate", None) == "23514"
    assert rejected.value.orig.diag.constraint_name in {
        "ck_job_events_state_shape",
        "ck_job_events_matches_job",
    }


def test_job_rejects_invalid_error_json_shapes(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            connection.execute(
                text(
                    """
                    UPDATE jobs
                    SET status='FAILED', terminal_at=:at, updated_at=:at,
                        error_code='SOURCE_POLICY_BLOCKED', error_title='Blocked',
                        error_detail='Policy blocked this source.', error_retryable=false,
                        error_correlation_id='corr-1', error_policy='[]'::jsonb,
                        error_actions='{}'::jsonb
                    """
                ),
                {"at": NOW + timedelta(seconds=1)},
            )
    assert_constraint(rejected.value, name="ck_jobs_error_payload")


def test_policy_view_rejects_nonpublic_official_url(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            connection.execute(
                text(
                    """
                    UPDATE jobs
                    SET status='FAILED', terminal_at=:at, updated_at=:at,
                        error_code='SOURCE_POLICY_BLOCKED', error_title='Blocked',
                        error_detail='Policy blocked this source.', error_retryable=false,
                        error_correlation_id='corr-1',
                        error_policy=CAST(:policy AS jsonb),
                        error_actions='["open_official"]'::jsonb
                    """
                ),
                {
                    "at": NOW + timedelta(seconds=1),
                    "policy": (
                        '{"decision":"block","permitted_operations":[],"name":"Blocked",'
                        '"official_url":"https://docs.example/path?token=secret",'
                        '"user_actions":["open_official"]}'
                    ),
                },
            )
    assert_constraint(rejected.value, name="ck_jobs_error_payload")


def test_request_confirmation_cannot_follow_creation(migrated_database: Engine) -> None:
    seed_rights(migrated_database)
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            insert_request(connection, rights_confirmed_at=NOW + timedelta(microseconds=1))
    assert_constraint(
        rejected.value,
        name="ck_source_resolution_requests_rights_time",
    )


def test_job_terminal_time_cannot_precede_creation(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            connection.execute(
                text(
                    """
                    UPDATE jobs
                    SET status='FAILED', updated_at=:updated, terminal_at=:terminal,
                        error_code='SOURCE_POLICY_BLOCKED', error_title='Blocked',
                        error_detail='Policy blocked this source.', error_retryable=false,
                        error_correlation_id='corr-1'
                    """
                ),
                {
                    "updated": NOW + timedelta(seconds=1),
                    "terminal": NOW - timedelta(seconds=1),
                },
            )
    assert_constraint(rejected.value, name="ck_jobs_time_order")


@pytest.mark.parametrize(
    "update",
    [
        """
        UPDATE outbox_messages
        SET published_at=:at, retention_eligible_at=:at + interval '22 hours',
            retention_must_purge_by=:at + interval '24 hours'
        """,
        """
        UPDATE outbox_messages
        SET claimed_by='dispatcher', claim_token='token', claimed_at=:at,
            lease_expires_at=:at + interval '60 seconds'
        """,
    ],
)
def test_outbox_lifecycle_requires_a_consumed_attempt(
    migrated_database: Engine,
    update: str,
) -> None:
    insert_aggregate(migrated_database)
    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(text(update), {"at": NOW + timedelta(seconds=1)})
    assert_constraint(rejected.value, name="ck_outbox_messages_lifecycle")
