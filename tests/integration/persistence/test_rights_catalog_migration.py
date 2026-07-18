"""Rights-catalog persistence contract."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.persistence._rights_catalog import assert_constraint, insert_statement

pytestmark = pytest.mark.integration


def test_migration_creates_append_only_catalog_contract(migrated_database: Engine) -> None:
    inspector = inspect(migrated_database)
    assert "rights_statement_catalog" in inspector.get_table_names()
    assert inspector.get_pk_constraint("rights_statement_catalog")["constrained_columns"] == [
        "version",
        "locale",
    ]

    check_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("rights_statement_catalog")
    }
    assert {
        "ck_rights_statement_catalog_hash_format",
        "ck_rights_statement_catalog_hash_matches_statement",
        "ck_rights_statement_catalog_locale_supported",
        "ck_rights_statement_catalog_statement_nonempty",
        "ck_rights_statement_catalog_version_format",
        "ck_rights_statement_catalog_expiry_order",
        "ck_rights_statement_catalog_supersede_order",
    } <= check_names

    with migrated_database.connect() as connection:
        exclusion_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM pg_constraint
                WHERE conrelid = 'rights_statement_catalog'::regclass
                  AND contype = 'x'
                """
            )
        )
    assert exclusion_count == 1


def test_catalog_rejects_invalid_hash_and_overlapping_locale_window(
    migrated_database: Engine,
) -> None:
    with pytest.raises(IntegrityError) as invalid_format:
        insert_statement(
            migrated_database,
            version="rights-2026-07-18.1",
            statement_hash="A" * 64,
        )
    assert_constraint(
        invalid_format.value,
        name="ck_rights_statement_catalog_hash_format",
    )

    with pytest.raises(IntegrityError) as hash_mismatch:
        insert_statement(
            migrated_database,
            version="rights-2026-07-18.1",
            statement_hash="a" * 64,
        )
    assert_constraint(
        hash_mismatch.value,
        name="ck_rights_statement_catalog_hash_matches_statement",
    )

    insert_statement(migrated_database, version="rights-2026-07-18.1")
    with pytest.raises(IntegrityError) as overlap:
        insert_statement(
            migrated_database,
            version="rights-2026-07-19.1",
            effective_at=datetime(2026, 7, 19, tzinfo=UTC),
        )
    assert_constraint(
        overlap.value,
        name="ex_rights_statement_catalog_current_window",
        sqlstate="23P01",
    )

    insert_statement(
        migrated_database,
        version="rights-2026-07-18.1",
        locale="en-US",
    )


@pytest.mark.parametrize(
    ("overrides", "constraint_name"),
    [
        ({"version": "invalid-version"}, "ck_rights_statement_catalog_version_format"),
        (
            {"version": "rights-2026-07-18.1", "locale": "fr-FR"},
            "ck_rights_statement_catalog_locale_supported",
        ),
        (
            {"version": "rights-2026-07-18.1", "statement": ""},
            "ck_rights_statement_catalog_statement_nonempty",
        ),
        (
            {
                "version": "rights-2026-07-18.1",
                "expires_at": datetime(2026, 7, 17, tzinfo=UTC),
            },
            "ck_rights_statement_catalog_expiry_order",
        ),
        (
            {
                "version": "rights-2026-07-18.1",
                "superseded_at": datetime(2026, 7, 17, tzinfo=UTC),
            },
            "ck_rights_statement_catalog_supersede_order",
        ),
    ],
)
def test_catalog_rejects_invalid_wire_and_lifecycle_values(
    migrated_database: Engine,
    overrides: dict[str, object],
    constraint_name: str,
) -> None:
    with pytest.raises(IntegrityError) as invalid:
        insert_statement(migrated_database, **overrides)  # type: ignore[arg-type]
    assert_constraint(invalid.value, name=constraint_name)


def test_catalog_only_allows_first_superseded_timestamp(migrated_database: Engine) -> None:
    version = "rights-2026-07-18.1"
    insert_statement(migrated_database, version=version)

    with (
        pytest.raises(IntegrityError) as combined_mutation,
        migrated_database.begin() as connection,
    ):
        connection.execute(
            text(
                """
                UPDATE rights_statement_catalog
                SET superseded_at = '2026-07-19T00:00:00Z', statement = 'changed'
                WHERE version = 'rights-2026-07-18.1' AND locale = 'zh-CN'
                """
            )
        )
    assert_constraint(
        combined_mutation.value,
        name="ck_rights_statement_catalog_append_only",
    )

    with migrated_database.begin() as connection:
        connection.execute(
            text(
                """
                UPDATE rights_statement_catalog
                SET superseded_at = '2026-07-19T00:00:00Z'
                WHERE version = 'rights-2026-07-18.1' AND locale = 'zh-CN'
                """
            )
        )

    for mutation in (
        "UPDATE rights_statement_catalog SET statement = 'changed' "
        "WHERE version = 'rights-2026-07-18.1'",
        "UPDATE rights_statement_catalog SET superseded_at = '2026-07-20T00:00:00Z' "
        "WHERE version = 'rights-2026-07-18.1'",
        "DELETE FROM rights_statement_catalog WHERE version = 'rights-2026-07-18.1'",
    ):
        with pytest.raises(IntegrityError) as rejected, migrated_database.begin() as connection:
            connection.execute(text(mutation))
        assert_constraint(
            rejected.value,
            name="ck_rights_statement_catalog_append_only",
        )

    with migrated_database.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT statement, superseded_at
                FROM rights_statement_catalog
                WHERE version = 'rights-2026-07-18.1' AND locale = 'zh-CN'
                """
            )
        ).one()
    assert row.statement == f"statement-{version}"
    assert row.superseded_at == datetime(2026, 7, 19, tzinfo=UTC)

    insert_statement(
        migrated_database,
        version="rights-2026-07-19.1",
        effective_at=datetime(2026, 7, 19, tzinfo=UTC),
    )
