"""Failure and retry contract for the PostgreSQL resolution-create writer."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine

from tests.integration.persistence._resolution_create_failures import (
    fail_outbox_with_serialization,
)
from tests.integration.persistence._resolution_create_store import (
    aggregate_counts,
    make_command,
    make_request,
    make_store,
    seed_current_rights,
)
from video_server.persistence.resolution_create import (
    CreateDisposition,
    ResolutionCreatePersistenceError,
)

pytestmark = pytest.mark.integration


def _assert_zero(engine: Engine) -> None:
    assert set(aggregate_counts(engine).values()) == {0}


def _assert_safe_internal_failure(error: ResolutionCreatePersistenceError) -> None:
    assert error.code == "INTERNAL_ERROR"
    assert error.retryable is False
    assert "postgresql" not in str(error).lower()


def test_invalid_idempotency_key_is_safely_mapped_before_database_work(
    migrated_database: Engine,
) -> None:
    raw_key = "too-short"

    with pytest.raises(ResolutionCreatePersistenceError) as rejected:
        make_store(migrated_database).create(make_command(key=raw_key))

    assert rejected.value.code == "IDEMPOTENCY_KEY_INVALID"
    assert rejected.value.retryable is False
    assert raw_key not in str(rejected.value)
    _assert_zero(migrated_database)


def test_unsupported_locale_is_rejected_without_database_writes(
    migrated_database: Engine,
) -> None:
    request = make_request(rights_statement_locale="fr-FR")

    with pytest.raises(ResolutionCreatePersistenceError) as rejected:
        make_store(migrated_database).create(make_command(request=request))

    assert rejected.value.code == "RIGHTS_STATEMENT_STALE"
    assert rejected.value.actions == ("refresh_rights_statement",)
    _assert_zero(migrated_database)


def test_missing_current_statement_is_retryable_and_writes_nothing(
    migrated_database: Engine,
) -> None:
    request = make_request(rights_statement_locale="en-US")

    with pytest.raises(ResolutionCreatePersistenceError) as unavailable:
        make_store(migrated_database).create(make_command(request=request))

    assert unavailable.value.code == "RIGHTS_STATEMENT_UNAVAILABLE"
    assert unavailable.value.retryable is True
    _assert_zero(migrated_database)


def test_autocommit_engine_is_rejected_before_any_aggregate_write(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    autocommit_engine = migrated_database.execution_options(isolation_level="AUTOCOMMIT")

    with pytest.raises(ResolutionCreatePersistenceError) as unavailable:
        make_store(autocommit_engine).create(make_command())

    _assert_safe_internal_failure(unavailable.value)
    _assert_zero(migrated_database)


def test_pool_timeout_does_not_expose_the_database_url(migrated_database: Engine) -> None:
    seed_current_rights(migrated_database)
    constrained = create_engine(
        migrated_database.url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.01,
    )
    rendered_url = constrained.url.render_as_string(hide_password=False)

    try:
        with (
            constrained.connect(),
            pytest.raises(ResolutionCreatePersistenceError) as unavailable,
        ):
            make_store(constrained).create(make_command())
    finally:
        constrained.dispose()

    _assert_safe_internal_failure(unavailable.value)
    assert rendered_url not in str(unavailable.value)
    _assert_zero(migrated_database)


def test_canonically_equivalent_url_replays_with_the_same_key(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)
    store = make_store(migrated_database)
    created = store.create(make_command())
    equivalent = make_request(url="https://MEDIA.EXAMPLE.:443/%76ideo")

    replayed = store.create(make_command(request=equivalent))

    assert created.disposition is CreateDisposition.CREATED
    assert replayed.disposition is CreateDisposition.REPLAYED
    assert (replayed.resolution_id, replayed.job_id) == (created.resolution_id, created.job_id)
    assert set(aggregate_counts(migrated_database).values()) == {1}


def test_serialization_failure_retries_the_whole_transaction_then_succeeds(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)

    with fail_outbox_with_serialization(migrated_database, failures=2) as attempts:
        result = make_store(migrated_database).create(make_command())
        assert attempts() == 3

    assert result.disposition is CreateDisposition.CREATED
    assert set(aggregate_counts(migrated_database).values()) == {1}


def test_serialization_retry_stops_after_three_whole_transactions(
    migrated_database: Engine,
) -> None:
    seed_current_rights(migrated_database)

    with (
        fail_outbox_with_serialization(migrated_database, failures=3) as attempts,
        pytest.raises(ResolutionCreatePersistenceError) as unavailable,
    ):
        make_store(migrated_database).create(make_command())
    assert attempts() == 3

    _assert_safe_internal_failure(unavailable.value)
    _assert_zero(migrated_database)
