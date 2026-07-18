"""Revision 0003 must reject pre-existing retroactive attestations."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._legacy_resolution_aggregate import insert_legacy_aggregate
from tests.integration.persistence._resolution_aggregate import NOW
from tests.integration.persistence._rights_catalog import assert_constraint

pytestmark = pytest.mark.integration

_CONSTRAINT = "ck_rights_statement_catalog_supersede_after_attestation"
_V1 = "rights-2026-07-18.1"
_V2 = "rights-2026-07-18.2"
_SUPERSEDED_AT = NOW + timedelta(hours=1)
_CONFIRMED_AT = NOW + timedelta(hours=2)
_V2_STATEMENT = f"statement-{_V2}"
_V2_HASH = hashlib.sha256(_V2_STATEMENT.encode()).hexdigest()


def _seed_retroactive_history(engine: Engine) -> None:
    insert_legacy_aggregate(engine, confirmed_at=_CONFIRMED_AT)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE rights_statement_catalog
                SET superseded_at=:superseded_at
                WHERE version=:version AND locale='zh-CN'
                """
            ),
            {"version": _V1, "superseded_at": _SUPERSEDED_AT},
        )
        connection.execute(
            text(
                """
                INSERT INTO rights_statement_catalog (
                    version, locale, statement, statement_sha256, effective_at
                ) VALUES (
                    :version, 'zh-CN', :statement, :statement_hash, :effective_at
                )
                """
            ),
            {
                "version": _V2,
                "statement": _V2_STATEMENT,
                "statement_hash": _V2_HASH,
                "effective_at": _SUPERSEDED_AT,
            },
        )


def _history_snapshot(engine: Engine) -> tuple[tuple[tuple[object, ...], ...], ...]:
    statements = (
        """
        SELECT version, locale, statement, statement_sha256,
               effective_at, expires_at, superseded_at
        FROM rights_statement_catalog
        ORDER BY locale, effective_at
        """,
        """
        SELECT id, owner_id, job_id, rights_statement_version,
               rights_statement_locale, rights_statement_sha256,
               rights_confirmed_at, created_at
        FROM source_resolution_requests
        ORDER BY id
        """,
    )
    with engine.connect() as connection:
        return tuple(
            tuple(tuple(row) for row in connection.execute(text(statement)))
            for statement in statements
        )


def _revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(connection.scalar(text("SELECT version_num FROM alembic_version")))


def _guard_definition(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(
            connection.scalar(
                text("SELECT pg_get_functiondef('guard_rights_statement_catalog()'::regprocedure)")
            )
        )


def test_0003_upgrade_rejects_existing_retroactive_attestation_history(
    migrated_database: Engine,
    alembic_config: Config,
) -> None:
    command.downgrade(alembic_config, "0002_resolution_aggregate")
    try:
        _seed_retroactive_history(migrated_database)
        before = _history_snapshot(migrated_database)
        assert _revision(migrated_database) == "0002_resolution_aggregate"

        with pytest.raises(IntegrityError) as rejected:
            command.upgrade(alembic_config, "head")

        assert_constraint(rejected.value, name=_CONSTRAINT)
        assert _revision(migrated_database) == "0002_resolution_aggregate"
        assert _history_snapshot(migrated_database) == before
        assert _CONSTRAINT not in _guard_definition(migrated_database)
    finally:
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
