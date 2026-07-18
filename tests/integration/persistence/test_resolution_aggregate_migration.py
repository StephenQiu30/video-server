"""Migration contract for the source-resolution create aggregate."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._identity import OTHER_USER_ID, insert_user
from tests.integration.persistence._job_event import insert_current_event
from tests.integration.persistence._resolution_aggregate import (
    ELIGIBLE_AT,
    JOB_ID,
    MUST_PURGE_BY,
    NOW,
    OWNER_ID,
    RESOLUTION_ID,
    insert_job,
    insert_request,
    seed_rights,
)
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration


def test_migration_creates_id_only_resolution_aggregate(migrated_database: Engine) -> None:
    inspector = inspect(migrated_database)
    assert {
        "jobs",
        "source_resolution_requests",
        "job_events",
        "outbox_messages",
    } <= set(inspector.get_table_names())
    assert inspector.get_pk_constraint("jobs")["constrained_columns"] == ["id"]
    assert inspector.get_pk_constraint("source_resolution_requests")["constrained_columns"] == [
        "id"
    ]
    assert inspector.get_pk_constraint("job_events")["constrained_columns"] == ["id"]
    assert inspector.get_pk_constraint("outbox_messages")["constrained_columns"] == ["id"]
    for table in ("job_events", "outbox_messages"):
        identity = next(
            column["identity"] for column in inspector.get_columns(table) if column["name"] == "id"
        )
        assert identity is not None and identity["always"] is True
    event_uniques = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspector.get_unique_constraints("job_events")
    }
    assert event_uniques["uq_job_events_job_snapshot"] == ["job_id", "occurred_at"]

    outbox_columns = {column["name"] for column in inspector.get_columns("outbox_messages")}
    assert {"resolution_request_id", "job_id", "owner_id", "kind"} <= outbox_columns
    assert not ({"payload", "url", "source_url", "selector"} & outbox_columns)


def test_request_foreign_keys_bind_owner_clock_and_rights(migrated_database: Engine) -> None:
    seed_rights(migrated_database)
    with migrated_database.begin() as connection:
        insert_job(connection)
        insert_current_event(connection)
        insert_user(connection, OTHER_USER_ID)

    for overrides, constraint_name in (
        ({"owner_id": OTHER_USER_ID}, "fk_source_resolution_requests_job_identity"),
        (
            {
                "created_at": NOW + timedelta(seconds=1),
                "detail_eligible_at": ELIGIBLE_AT + timedelta(seconds=1),
                "detail_must_purge_by": MUST_PURGE_BY + timedelta(seconds=1),
            },
            "fk_source_resolution_requests_job_identity",
        ),
        ({"rights_statement_sha256": "f" * 64}, "fk_source_resolution_requests_rights"),
    ):
        with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
            insert_request(connection, **overrides)
        assert_constraint(rejected.value, name=constraint_name, sqlstate="23503")


@pytest.mark.parametrize(
    ("overrides", "constraint_name"),
    [
        ({"id": "res:unsafe"}, "ck_source_resolution_requests_id_format"),
        ({"idempotency_key_digest": "A" * 64}, "ck_source_resolution_requests_key_digest"),
        ({"request_digest": "f" * 63}, "ck_source_resolution_requests_request_digest"),
        ({"url_ciphertext": b"x" * 16}, "ck_source_resolution_requests_ciphertext"),
        ({"url_nonce": b"n" * 23}, "ck_source_resolution_requests_nonce"),
        ({"url_wrapped_dek": b"w" * 47}, "ck_source_resolution_requests_wrapped_dek"),
        ({"url_wrap_nonce": b"r" * 25}, "ck_source_resolution_requests_wrap_nonce"),
        ({"url_key_id": ""}, "ck_source_resolution_requests_key_id"),
        (
            {"detail_eligible_at": ELIGIBLE_AT + timedelta(seconds=1)},
            "ck_source_resolution_requests_retention",
        ),
        (
            {"detail_must_purge_by": MUST_PURGE_BY + timedelta(seconds=1)},
            "ck_source_resolution_requests_retention",
        ),
    ],
)
def test_request_rejects_unsafe_identity_envelope_and_retention(
    migrated_database: Engine,
    overrides: dict[str, object],
    constraint_name: str,
) -> None:
    seed_rights(migrated_database)
    with migrated_database.begin() as connection:
        insert_job(connection)
        with pytest.raises(IntegrityError) as rejected:
            insert_request(connection, **overrides)
    assert_constraint(rejected.value, name=constraint_name)


def test_request_scope_and_job_are_one_to_one(migrated_database: Engine) -> None:
    seed_rights(migrated_database)
    with migrated_database.begin() as connection:
        insert_job(connection)
        insert_request(connection)
        insert_current_event(connection)

    with pytest.raises(IntegrityError) as duplicate_scope, migrated_database.begin() as connection:
        insert_request(connection, id="res_01J3H5N7Q9S1V3X5Z7A9C1E3G6")
    assert_constraint(
        duplicate_scope.value,
        name="uq_source_resolution_requests_idempotency_scope",
        sqlstate="23505",
    )

    with migrated_database.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT id, job_id, owner_id, detail_eligible_at, detail_must_purge_by
                FROM source_resolution_requests
                """
            )
        ).one()
    assert (row.id, row.job_id, row.owner_id) == (RESOLUTION_ID, JOB_ID, OWNER_ID)
    assert (row.detail_eligible_at, row.detail_must_purge_by) == (
        ELIGIBLE_AT,
        MUST_PURGE_BY,
    )
