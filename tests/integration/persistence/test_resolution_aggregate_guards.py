"""Database guards for the source-resolution create aggregate."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._identity import OTHER_USER_ID, insert_user
from tests.integration.persistence._job_event import insert_current_event
from tests.integration.persistence._resolution_aggregate import (
    ELIGIBLE_AT,
    MUST_PURGE_BY,
    NOW,
    insert_aggregate,
    insert_event,
    insert_job,
    insert_outbox,
    insert_request,
    seed_rights,
)
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "RUNNING", "attempt": 1},
        {"stage": "CHECKING_POLICY"},
        {"attempt": 1},
        {"progress": 0},
        {"updated_at": NOW + timedelta(seconds=1)},
    ],
)
def test_jobs_can_only_be_inserted_in_the_exact_initial_state(
    migrated_database: Engine,
    overrides: dict[str, object],
) -> None:
    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        insert_job(connection, **overrides)
    assert_constraint(rejected.value, name="ck_jobs_initial_state")


def test_terminal_jobs_and_monotonic_state_cannot_move_backward(
    migrated_database: Engine,
) -> None:
    with migrated_database.begin() as connection:
        insert_job(connection)
        insert_current_event(connection)
        connection.execute(
            text(
                """
                UPDATE jobs
                SET status='FAILED', error_code='SOURCE_POLICY_BLOCKED',
                    error_title='Blocked', error_detail='Policy blocked this source.',
                    error_retryable=false, error_correlation_id='corr-1',
                    terminal_at=:terminal_at, updated_at=:terminal_at
                """
            ),
            {"terminal_at": NOW + timedelta(seconds=1)},
        )
        insert_current_event(connection)

    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(text("UPDATE jobs SET status='RUNNING', attempt=1, terminal_at=NULL"))
    assert_constraint(rejected.value, name="ck_jobs_transition")


def test_request_only_allows_complete_kek_rewrap(migrated_database: Engine) -> None:
    insert_aggregate(migrated_database)
    with migrated_database.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE source_resolution_requests
                SET url_wrapped_dek=:wrapped, url_wrap_nonce=:nonce, url_key_id='kek-2'
                """
            ),
            {"wrapped": b"z" * 48, "nonce": b"q" * 24},
        )

    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(
            text("UPDATE source_resolution_requests SET owner_id=:owner_id"),
            {"owner_id": OTHER_USER_ID},
        )
    assert_constraint(rejected.value, name="ck_source_resolution_requests_immutable")


def test_job_events_only_delete_with_the_complete_aggregate(migrated_database: Engine) -> None:
    insert_aggregate(migrated_database)
    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(text("UPDATE job_events SET progress=1"))
    assert_constraint(rejected.value, name="ck_job_events_append_only")

    with pytest.raises(IntegrityError) as orphaned, migrated_database.begin() as connection:
        connection.execute(text("DELETE FROM job_events"))
    assert_constraint(orphaned.value, name="ck_job_events_append_only")

    with pytest.raises(IntegrityError) as truncated, migrated_database.begin() as connection:
        connection.execute(text("TRUNCATE job_events"))
    assert_constraint(truncated.value, name="ck_job_events_append_only")

    with migrated_database.begin() as connection:
        connection.execute(text("DELETE FROM outbox_messages"))
        connection.execute(text("DELETE FROM source_resolution_requests"))
        connection.execute(text("DELETE FROM job_events"))
        connection.execute(text("DELETE FROM jobs"))


def test_event_and_outbox_require_exact_aggregate_identity(migrated_database: Engine) -> None:
    seed_rights(migrated_database)
    with migrated_database.begin() as connection:
        insert_job(connection)
        insert_request(connection)
        insert_current_event(connection)
        insert_user(connection, OTHER_USER_ID)

    with pytest.raises(IntegrityError) as bad_event, migrated_database.begin() as connection:
        insert_event(
            connection,
            owner_id=OTHER_USER_ID,
            occurred_at=NOW + timedelta(seconds=1),
        )
    assert_constraint(bad_event.value, name="fk_job_events_job_identity", sqlstate="23503")

    with pytest.raises(IntegrityError) as bad_outbox, migrated_database.begin() as connection:
        insert_outbox(
            connection,
            aggregate_created_at=NOW + timedelta(seconds=1),
            retention_eligible_at=ELIGIBLE_AT + timedelta(seconds=1),
            retention_must_purge_by=MUST_PURGE_BY + timedelta(seconds=1),
        )
    assert_constraint(
        bad_outbox.value,
        name="fk_outbox_messages_resolution_identity",
        sqlstate="23503",
    )


@pytest.mark.parametrize(
    ("overrides", "constraint_name"),
    [
        ({"kind": "ARBITRARY"}, "ck_outbox_messages_kind"),
        ({"attempts": 1}, "ck_outbox_messages_initial_state"),
        ({"lease_version": 1}, "ck_outbox_messages_initial_state"),
        (
            {"retention_eligible_at": ELIGIBLE_AT + timedelta(seconds=1)},
            "ck_outbox_messages_retention",
        ),
        (
            {"retention_must_purge_by": MUST_PURGE_BY + timedelta(seconds=1)},
            "ck_outbox_messages_retention",
        ),
    ],
)
def test_outbox_insert_is_fixed_id_only_initial_state(
    migrated_database: Engine,
    overrides: dict[str, object],
    constraint_name: str,
) -> None:
    seed_rights(migrated_database)
    with migrated_database.begin() as connection:
        insert_job(connection)
        insert_request(connection)
        with pytest.raises(IntegrityError) as rejected:
            insert_outbox(connection, **overrides)
    assert_constraint(rejected.value, name=constraint_name)
