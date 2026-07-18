"""Cross-row coherence guards for the resolution create aggregate."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._resolution_aggregate import (
    JOB_ID,
    NOW,
    OWNER_ID,
    RESOLUTION_ID,
    insert_aggregate,
    insert_event,
    insert_job,
    insert_request,
)
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("status", "error_sql"),
    [
        ("RETRY_WAIT", ""),
        (
            "FAILED",
            """
            , terminal_at=:at, error_code='SOURCE_POLICY_BLOCKED',
              error_title='Blocked', error_detail='Policy blocked this source.',
              error_retryable=false, error_correlation_id='corr-1'
            """,
        ),
    ],
)
def test_wait_and_failure_preserve_the_last_running_snapshot(
    migrated_database: Engine,
    status: str,
    error_sql: str,
) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        connection.execute(
            text(
                """
                UPDATE jobs SET status='RUNNING', stage='CHECKING_POLICY',
                    attempt=1, progress=20, updated_at=:at
                """
            ),
            {"at": NOW + timedelta(seconds=1)},
        )
        with pytest.raises(IntegrityError) as rejected:
            connection.execute(
                text(
                    f"""
                    UPDATE jobs SET status=:status, stage='EXTRACTING_METADATA',
                        progress=30, updated_at=:at {error_sql}
                    """
                ),
                {"status": status, "at": NOW + timedelta(seconds=2)},
            )
    assert_constraint(rejected.value, name="ck_jobs_transition")


def test_error_policy_rejects_extra_keys_and_duplicate_actions(
    migrated_database: Engine,
) -> None:
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
                        error_policy='{"secret":"must-not-persist"}'::jsonb,
                        error_actions='["retry_resolution","retry_resolution"]'::jsonb
                    """
                ),
                {"at": NOW + timedelta(seconds=1)},
            )
    assert_constraint(rejected.value, name="ck_jobs_error_payload")


def test_event_snapshot_must_match_the_current_job(migrated_database: Engine) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            insert_event(
                connection,
                status="SUCCEEDED",
                stage="READY",
                attempt=1,
                progress=100,
                occurred_at=NOW + timedelta(seconds=1),
            )
    assert_constraint(rejected.value, name="ck_job_events_matches_job")


def test_outbox_identity_cannot_retarget_another_valid_aggregate(
    migrated_database: Engine,
) -> None:
    insert_aggregate(migrated_database)
    second_job = "job_01J3H5N7Q9S1V3X5Z7A9C1E3G6"
    second_request = "res_01J3H5N7Q9S1V3X5Z7A9C1E3G6"
    with migrated_database.begin() as connection:
        insert_job(connection, id=second_job)
        insert_request(
            connection,
            id=second_request,
            job_id=second_job,
            idempotency_key_digest="3" * 64,
            request_digest="4" * 64,
        )
        with pytest.raises(IntegrityError) as rejected:
            connection.execute(
                text(
                    """
                    UPDATE outbox_messages
                    SET resolution_request_id=:request_id, job_id=:job_id
                    WHERE resolution_request_id=:original_request_id
                    """
                ),
                {
                    "request_id": second_request,
                    "job_id": second_job,
                    "original_request_id": RESOLUTION_ID,
                },
            )
    assert_constraint(rejected.value, name="ck_outbox_messages_immutable")


def test_database_requires_positive_monotonic_ids(migrated_database: Engine) -> None:
    inspector = inspect(migrated_database)
    for table in ("job_events", "outbox_messages"):
        checks = {item["name"] for item in inspector.get_check_constraints(table)}
        assert f"ck_{table}_id_positive" in checks

    with migrated_database.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM jobs WHERE id=:id AND owner_id=:owner"),
                {"id": JOB_ID, "owner": OWNER_ID},
            )
            == 0
        )
