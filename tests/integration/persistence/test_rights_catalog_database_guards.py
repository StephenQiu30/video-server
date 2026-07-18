"""Database-only guards for the append-only rights catalog."""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._rights_catalog import assert_constraint, insert_statement

pytestmark = pytest.mark.integration

_INFINITE_INSERTS = {
    "effective_negative": """
        INSERT INTO rights_statement_catalog (
            version, locale, statement, statement_sha256, effective_at
        ) VALUES (
            :version, 'zh-CN', :statement, :statement_hash, '-infinity'::timestamptz
        )
    """,
    "effective_positive": """
        INSERT INTO rights_statement_catalog (
            version, locale, statement, statement_sha256, effective_at
        ) VALUES (
            :version, 'zh-CN', :statement, :statement_hash, 'infinity'::timestamptz
        )
    """,
    "expiry": """
        INSERT INTO rights_statement_catalog (
            version, locale, statement, statement_sha256, effective_at, expires_at
        ) VALUES (
            :version, 'zh-CN', :statement, :statement_hash,
            '2026-07-18T00:00:00Z', 'infinity'::timestamptz
        )
    """,
    "supersede": """
        INSERT INTO rights_statement_catalog (
            version, locale, statement, statement_sha256, effective_at, superseded_at
        ) VALUES (
            :version, 'zh-CN', :statement, :statement_hash,
            '2026-07-18T00:00:00Z', 'infinity'::timestamptz
        )
    """,
}


@pytest.mark.parametrize(
    ("case", "constraint_name"),
    [
        ("effective_negative", "ck_rights_statement_catalog_effective_finite"),
        ("effective_positive", "ck_rights_statement_catalog_effective_finite"),
        ("expiry", "ck_rights_statement_catalog_expiry_finite"),
        ("supersede", "ck_rights_statement_catalog_supersede_finite"),
    ],
)
def test_catalog_rejects_postgres_infinite_times(
    migrated_database: Engine,
    case: str,
    constraint_name: str,
) -> None:
    statement = f"statement-{case}"
    parameters = {
        "version": "rights-2026-07-18.1",
        "statement": statement,
        "statement_hash": hashlib.sha256(statement.encode()).hexdigest(),
    }
    with pytest.raises(IntegrityError) as invalid, migrated_database.begin() as connection:
        connection.execute(text(_INFINITE_INSERTS[case]), parameters)
    assert_constraint(invalid.value, name=constraint_name)


def test_catalog_rejects_truncate_and_preserves_rows(migrated_database: Engine) -> None:
    insert_statement(migrated_database, version="rights-2026-07-18.1")

    with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
        connection.execute(text("TRUNCATE rights_statement_catalog"))
    assert_constraint(
        rejected.value,
        name="ck_rights_statement_catalog_append_only",
    )

    with migrated_database.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM rights_statement_catalog")) == 1
