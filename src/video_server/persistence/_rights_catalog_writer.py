"""Internal SQL operations for atomic rights-catalog imports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import Connection, text
from sqlalchemy.engine import RowMapping

from video_server.persistence._advisory_locks import (
    SUPPORTED_RIGHTS_LOCALES,
    lock_rights_locales,
)
from video_server.source.rights import RightsCatalogEntry

_SELECT_ALL = text(
    """
    SELECT version, locale, statement, statement_sha256,
           effective_at, expires_at, superseded_at
    FROM rights_statement_catalog
    ORDER BY locale, effective_at
    FOR UPDATE
    """
)
_SUPERSEDE_ENTRY = text(
    """
    UPDATE rights_statement_catalog
    SET superseded_at = :superseded_at
    WHERE version = :version AND locale = :locale AND superseded_at IS NULL
    """
)
_INSERT_ENTRY = text(
    """
    INSERT INTO rights_statement_catalog (
        version, locale, statement, statement_sha256,
        effective_at, expires_at, superseded_at
    ) VALUES (
        :version, :locale, :statement, :statement_sha256,
        :effective_at, :expires_at, :superseded_at
    )
    """
)
_SELECT_LATEST_ATTESTATION = text(
    """
    SELECT max(rights_confirmed_at)
    FROM source_resolution_requests
    WHERE rights_statement_version = :version
      AND rights_statement_locale = :locale
    """
)
_IMMUTABLE_FIELDS = (
    "version",
    "locale",
    "statement",
    "statement_sha256",
    "effective_at",
    "expires_at",
)


class CatalogConflictSignal(Exception):
    """Internal rollback signal translated at the public boundary."""


class UnsafeTransactionSignal(Exception):
    """The DBAPI connection cannot provide atomic catalog writes."""


def import_catalog_entries(
    connection: Connection,
    entries: Sequence[RightsCatalogEntry],
) -> tuple[int, int, int]:
    _ensure_transactional(connection)
    _validate_snapshot(entries)
    _lock_locales(connection)
    existing_rows = connection.execute(_SELECT_ALL).mappings().all()
    existing_by_identity = {(row["version"], row["locale"]): row for row in existing_rows}
    incoming_identities = {(entry.statement.version, entry.statement.locale) for entry in entries}
    if not set(existing_by_identity).issubset(incoming_identities):
        raise CatalogConflictSignal

    inserts: list[dict[str, object]] = []
    supersedes: list[dict[str, object]] = []
    replayed = 0

    for entry in entries:
        values = _entry_values(entry)
        existing = existing_by_identity.get((values["version"], values["locale"]))
        if existing is None:
            inserts.append(values)
        elif not _same_immutable(existing, values):
            raise CatalogConflictSignal
        elif existing["superseded_at"] == values["superseded_at"]:
            replayed += 1
        elif existing["superseded_at"] is None and values["superseded_at"] is not None:
            supersedes.append(values)
        else:
            raise CatalogConflictSignal

    for values in supersedes:
        _ensure_supersession_preserves_attestations(connection, values)
        result = connection.execute(_SUPERSEDE_ENTRY, values)
        if result.rowcount != 1:
            raise CatalogConflictSignal
    for values in inserts:
        connection.execute(_INSERT_ENTRY, values)
    return len(inserts), replayed, len(supersedes)


def _ensure_transactional(connection: Connection) -> None:
    driver_connection = connection.connection.driver_connection
    if getattr(driver_connection, "autocommit", None) is not False:
        raise UnsafeTransactionSignal


def _validate_snapshot(entries: Sequence[RightsCatalogEntry]) -> None:
    locales = {entry.statement.locale for entry in entries}
    if locales != set(SUPPORTED_RIGHTS_LOCALES):
        raise CatalogConflictSignal
    successor_starts = {(entry.statement.locale, entry.statement.effective_at) for entry in entries}
    for entry in entries:
        if (
            entry.superseded_at is not None
            and (
                entry.statement.locale,
                entry.superseded_at,
            )
            not in successor_starts
        ):
            raise CatalogConflictSignal


def _lock_locales(connection: Connection) -> None:
    lock_rights_locales(connection, SUPPORTED_RIGHTS_LOCALES)


def _entry_values(entry: RightsCatalogEntry) -> dict[str, object]:
    statement = entry.statement
    return {
        "version": statement.version,
        "locale": statement.locale,
        "statement": statement.statement,
        "statement_sha256": statement.statement_sha256,
        "effective_at": statement.effective_at,
        "expires_at": statement.expires_at,
        "superseded_at": entry.superseded_at,
    }


def _ensure_supersession_preserves_attestations(
    connection: Connection,
    values: Mapping[str, object],
) -> None:
    latest = connection.scalar(_SELECT_LATEST_ATTESTATION, values)
    superseded_at = values["superseded_at"]
    if latest is not None and superseded_at <= latest:
        raise CatalogConflictSignal


def _same_immutable(
    existing: RowMapping,
    incoming: Mapping[str, object],
) -> bool:
    return all(existing[field] == incoming[field] for field in _IMMUTABLE_FIELDS)
