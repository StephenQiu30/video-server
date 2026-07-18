"""Migration contract for catalog supersession versus durable attestations."""

from __future__ import annotations

from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._resolution_aggregate import (
    NOW,
    insert_event,
    insert_job,
    insert_outbox,
    insert_request,
    seed_rights,
)
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration

_CONSTRAINT = "ck_rights_statement_catalog_supersede_after_attestation"
_CONFIRMED_AT = NOW + timedelta(hours=2)
_BASE_TRIGGERS = {
    "tr_rights_statement_catalog_append_only",
    "tr_rights_statement_catalog_no_truncate",
}
_UPDATE_SUPERSEDED_AT = text(
    """
    UPDATE rights_statement_catalog
    SET superseded_at=:superseded_at
    WHERE version='rights-2026-07-18.1' AND locale='zh-CN'
    """
)


def _seed_attestation(engine: Engine) -> None:
    seed_rights(engine)
    eligible_at = _CONFIRMED_AT + timedelta(hours=166)
    must_purge_by = _CONFIRMED_AT + timedelta(hours=168)
    times = {
        "created_at": _CONFIRMED_AT,
        "detail_eligible_at": eligible_at,
        "detail_must_purge_by": must_purge_by,
    }
    with engine.begin() as connection:
        insert_job(connection, updated_at=_CONFIRMED_AT, **times)
        insert_request(connection, rights_confirmed_at=_CONFIRMED_AT, **times)
        insert_event(
            connection,
            aggregate_created_at=_CONFIRMED_AT,
            occurred_at=_CONFIRMED_AT,
            detail_eligible_at=eligible_at,
            detail_must_purge_by=must_purge_by,
        )
        insert_outbox(
            connection,
            aggregate_created_at=_CONFIRMED_AT,
            retention_eligible_at=eligible_at,
            retention_must_purge_by=must_purge_by,
        )


def _history_snapshot(engine: Engine) -> tuple[object, ...]:
    with engine.connect() as connection:
        return tuple(
            connection.execute(
                text(
                    """
                    SELECT c.version, c.locale, c.statement_sha256,
                           c.effective_at, c.expires_at, c.superseded_at,
                           r.id, r.job_id, r.rights_confirmed_at, r.created_at
                    FROM rights_statement_catalog AS c
                    JOIN source_resolution_requests AS r
                      ON r.rights_statement_version = c.version
                     AND r.rights_statement_locale = c.locale
                     AND r.rights_statement_sha256 = c.statement_sha256
                    """
                )
            ).one()
        )


def _public_function_definitions(engine: Engine) -> str:
    with engine.connect() as connection:
        definitions = connection.scalars(
            text(
                """
                SELECT pg_get_functiondef(p.oid)
                FROM pg_proc AS p
                JOIN pg_namespace AS n ON n.oid = p.pronamespace
                WHERE n.nspname = current_schema()
                  AND p.prokind = 'f'
                ORDER BY p.proname
                """
            )
        ).all()
    return "\n".join(str(definition) for definition in definitions)


def _catalog_triggers(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        return set(
            connection.scalars(
                text(
                    """
                    SELECT t.tgname
                    FROM pg_trigger AS t
                    JOIN pg_class AS c ON c.oid = t.tgrelid
                    JOIN pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE n.nspname = current_schema()
                      AND c.relname = 'rights_statement_catalog'
                      AND NOT t.tgisinternal
                    """
                )
            )
        )


@pytest.mark.parametrize("offset_hours", [1, 2], ids=["before", "equal"])
def test_direct_supersession_cannot_rewrite_attestation_history(
    migrated_database: Engine,
    offset_hours: int,
) -> None:
    _seed_attestation(migrated_database)
    before = _history_snapshot(migrated_database)

    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(
            _UPDATE_SUPERSEDED_AT,
            {"superseded_at": NOW + timedelta(hours=offset_hours)},
        )

    assert_constraint(rejected.value, name=_CONSTRAINT)
    assert _history_snapshot(migrated_database) == before


def test_direct_supersession_strictly_after_confirmation_is_allowed(
    migrated_database: Engine,
) -> None:
    _seed_attestation(migrated_database)
    before = _history_snapshot(migrated_database)
    allowed_at = _CONFIRMED_AT + timedelta(hours=1)

    with migrated_database.begin() as connection:
        connection.execute(_UPDATE_SUPERSEDED_AT, {"superseded_at": allowed_at})

    after = _history_snapshot(migrated_database)
    assert after == (*before[:5], allowed_at, *before[6:])


def test_0003_round_trip_restores_0002_guard_without_residue(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    _seed_attestation(migrated_database)
    assert _CONSTRAINT in _public_function_definitions(migrated_database)

    command.downgrade(alembic_config, "0002_resolution_aggregate")
    try:
        downgraded = _public_function_definitions(migrated_database)
        assert _CONSTRAINT not in downgraded
        assert "ck_rights_statement_catalog_append_only" in downgraded
        assert _catalog_triggers(migrated_database) == _BASE_TRIGGERS
    finally:
        command.upgrade(alembic_config, "head")

    assert _CONSTRAINT in _public_function_definitions(migrated_database)
    before = _history_snapshot(migrated_database)
    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(_UPDATE_SUPERSEDED_AT, {"superseded_at": _CONFIRMED_AT})
    assert_constraint(rejected.value, name=_CONSTRAINT)
    assert _history_snapshot(migrated_database) == before
