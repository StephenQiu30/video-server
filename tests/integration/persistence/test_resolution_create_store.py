from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import Engine, text

from tests.integration.persistence._resolution_aggregate import (
    ELIGIBLE_AT,
    JOB_ID,
    MUST_PURGE_BY,
    NOW,
    OWNER_ID,
    RESOLUTION_ID,
)
from tests.integration.persistence._resolution_create_store import (
    HMAC_KEY,
    IDEMPOTENCY_KEY,
    RIGHTS_CHANGE_AT,
    URL,
    MutableClock,
    aggregate_counts,
    decrypt_request_url,
    expected_attestation,
    fail_inserts,
    make_command,
    make_request,
    make_store,
    persisted_aggregate_text,
    seed_current_rights,
    supersede_rights,
)
from video_server.job.state import JobStage, JobStatus
from video_server.persistence.resolution_create import (
    CreateDisposition,
    ResolutionCreatePersistenceError,
)

pytestmark = pytest.mark.integration


def test_create_atomically_persists_the_exact_initial_aggregate(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    result = make_store(migrated_database).create(make_command())

    assert (
        result.disposition,
        result.resolution_id,
        result.job_id,
        result.status,
        result.stage,
        result.created_at,
    ) == (
        CreateDisposition.CREATED,
        RESOLUTION_ID,
        JOB_ID,
        JobStatus.QUEUED,
        JobStage.VALIDATING_URL,
        NOW,
    )
    with migrated_database.connect() as connection:
        job = connection.execute(text("SELECT * FROM jobs")).mappings().one()
        request = (
            connection.execute(text("SELECT * FROM source_resolution_requests")).mappings().one()
        )
        event = connection.execute(text("SELECT * FROM job_events")).mappings().one()
        outbox = connection.execute(text("SELECT * FROM outbox_messages")).mappings().one()

    assert (job["owner_id"], job["status"], job["stage"], job["attempt"], job["progress"]) == (
        OWNER_ID,
        "QUEUED",
        "VALIDATING_URL",
        0,
        None,
    )
    assert (request["operation"], request["job_id"], request["created_at"]) == (
        "probe",
        JOB_ID,
        NOW,
    )
    assert (
        request["rights_statement_version"],
        request["rights_statement_locale"],
        request["rights_statement_sha256"],
    ) == expected_attestation()
    assert request["rights_confirmed_at"] == NOW
    assert (event["status"], event["stage"], event["attempt"], event["occurred_at"]) == (
        "QUEUED",
        "VALIDATING_URL",
        0,
        NOW,
    )
    assert (outbox["kind"], outbox["attempts"], outbox["lease_version"]) == (
        "SOURCE_RESOLUTION_REQUESTED",
        0,
        0,
    )
    for row in (job, request, event):
        assert (row["detail_eligible_at"], row["detail_must_purge_by"]) == (
            ELIGIBLE_AT,
            MUST_PURGE_BY,
        )


def test_url_uses_the_frozen_aad_and_no_raw_secret_is_persisted(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    make_store(migrated_database).create(make_command())

    assert decrypt_request_url(migrated_database) == URL.encode()
    persisted = persisted_aggregate_text(migrated_database)
    assert URL not in persisted
    assert IDEMPOTENCY_KEY not in persisted
    assert HMAC_KEY.hex() not in persisted


def test_same_key_and_request_replays_before_revalidating_stale_rights(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    clock = MutableClock()
    store = make_store(migrated_database, clock=clock)
    created = store.create(make_command())
    supersede_rights(migrated_database)
    clock.value = RIGHTS_CHANGE_AT + timedelta(seconds=1)

    replayed = store.create(make_command())

    assert replayed.disposition is CreateDisposition.REPLAYED
    assert (replayed.resolution_id, replayed.job_id, replayed.created_at) == (
        created.resolution_id,
        created.job_id,
        created.created_at,
    )
    assert set(aggregate_counts(migrated_database).values()) == {1}


@pytest.mark.parametrize("failure_kind", ["false", "stale"])
def test_conflict_wins_over_false_or_stale_rights(
    migrated_database: Engine,
    failure_kind: str,
) -> None:
    seed_current_rights(migrated_database)
    clock = MutableClock()
    store = make_store(migrated_database, clock=clock)
    store.create(make_command())
    if failure_kind == "false":
        request = make_request(rights_confirmed=False)
    else:
        supersede_rights(migrated_database)
        clock.value = RIGHTS_CHANGE_AT + timedelta(seconds=1)
        request = make_request(url="https://media.example/changed")

    with pytest.raises(ResolutionCreatePersistenceError) as conflict:
        store.create(make_command(request=request))

    assert conflict.value.code == "IDEMPOTENCY_CONFLICT"
    assert set(aggregate_counts(migrated_database).values()) == {1}


@pytest.mark.parametrize("failure_kind", ["false", "stale"])
def test_new_false_or_stale_request_writes_nothing(
    migrated_database: Engine,
    failure_kind: str,
) -> None:
    seed_current_rights(migrated_database)
    clock = MutableClock()
    if failure_kind == "false":
        request = make_request(rights_confirmed=False)
        expected = "RIGHTS_CONFIRMATION_REQUIRED"
    else:
        supersede_rights(migrated_database)
        clock.value = RIGHTS_CHANGE_AT + timedelta(seconds=1)
        request = make_request()
        expected = "RIGHTS_STATEMENT_STALE"

    with pytest.raises(ResolutionCreatePersistenceError) as rejected:
        make_store(migrated_database, clock=clock).create(make_command(request=request))

    assert rejected.value.code == expected
    assert set(aggregate_counts(migrated_database).values()) == {0}


@pytest.mark.parametrize("table", ["job_events", "outbox_messages"])
def test_event_or_outbox_failure_rolls_back_the_whole_aggregate(
    migrated_database: Engine,
    table: str,
) -> None:
    seed_current_rights(migrated_database)
    with (
        fail_inserts(migrated_database, table),
        pytest.raises(ResolutionCreatePersistenceError),
    ):
        make_store(migrated_database).create(make_command())

    assert set(aggregate_counts(migrated_database).values()) == {0}
