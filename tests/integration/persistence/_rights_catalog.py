"""Rights-catalog integration-test helpers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

EFFECTIVE_AT = datetime(2026, 7, 18, tzinfo=UTC)


def insert_statement(
    engine: Engine,
    *,
    version: str,
    locale: str = "zh-CN",
    statement: str | None = None,
    statement_hash: str | None = None,
    effective_at: datetime = EFFECTIVE_AT,
    expires_at: datetime | None = None,
    superseded_at: datetime | None = None,
) -> None:
    statement = statement if statement is not None else f"statement-{version}"
    statement_hash = statement_hash or hashlib.sha256(statement.encode()).hexdigest()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO rights_statement_catalog (
                    version, locale, statement, statement_sha256, effective_at,
                    expires_at, superseded_at
                ) VALUES (
                    :version, :locale, :statement, :statement_hash, :effective_at,
                    :expires_at, :superseded_at
                )
                """
            ),
            {
                "version": version,
                "locale": locale,
                "statement": statement,
                "statement_hash": statement_hash,
                "effective_at": effective_at,
                "expires_at": expires_at,
                "superseded_at": superseded_at,
            },
        )


def assert_constraint(
    error: IntegrityError,
    *,
    name: str,
    sqlstate: str = "23514",
) -> None:
    assert getattr(error.orig, "sqlstate", None) == sqlstate
    assert getattr(getattr(error.orig, "diag", None), "constraint_name", None) == name
