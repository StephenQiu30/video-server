"""Transactional PostgreSQL rights-catalog boundary."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from video_server.errors import DomainError
from video_server.persistence._rights_catalog_writer import (
    CatalogConflictSignal,
    UnsafeTransactionSignal,
    import_catalog_entries,
)
from video_server.source.rights import RightsCatalog

_RETRYABLE_TRANSACTION_STATES = frozenset({"40001", "40P01"})
_CATALOG_CONFLICT_STATES = frozenset({"23505", "23P01"})
_MAX_TRANSACTION_ATTEMPTS = 3


class RightsCatalogPersistenceError(DomainError):
    """A catalog document conflicts with durable catalog history."""


@dataclass(frozen=True, slots=True)
class CatalogImportResult:
    inserted: int
    replayed: int
    superseded: int

    def __post_init__(self) -> None:
        for field, value in (
            ("inserted", self.inserted),
            ("replayed", self.replayed),
            ("superseded", self.superseded),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")


class PostgresRightsCatalogStore:
    """Import a validated catalog as one PostgreSQL transaction."""

    __slots__ = ("_engine",)

    def __init__(self, engine: Engine) -> None:
        if not isinstance(engine, Engine):
            raise TypeError("engine must be a SQLAlchemy Engine")
        self._engine = engine

    def import_catalog(self, catalog: RightsCatalog) -> CatalogImportResult:
        if not isinstance(catalog, RightsCatalog):
            raise TypeError("catalog must be a RightsCatalog")
        for attempt in range(_MAX_TRANSACTION_ATTEMPTS):
            try:
                with self._engine.begin() as connection:
                    counts = import_catalog_entries(connection, catalog.entries)
                return CatalogImportResult(*counts)
            except CatalogConflictSignal:
                raise _conflict() from None
            except UnsafeTransactionSignal:
                raise _unavailable() from None
            except DBAPIError as error:
                sqlstate = getattr(error.orig, "sqlstate", None)
                if sqlstate in _RETRYABLE_TRANSACTION_STATES:
                    if attempt + 1 < _MAX_TRANSACTION_ATTEMPTS:
                        continue
                    raise _unavailable() from None
                if sqlstate in _CATALOG_CONFLICT_STATES:
                    raise _conflict() from None
                raise _unavailable() from None
            except SQLAlchemyError:
                raise _unavailable() from None
        raise AssertionError("transaction retry loop exhausted")


def _conflict() -> RightsCatalogPersistenceError:
    return RightsCatalogPersistenceError(
        "RIGHTS_CATALOG_CONFLICT",
        "The rights catalog conflicts with durable history.",
    )


def _unavailable() -> RightsCatalogPersistenceError:
    return RightsCatalogPersistenceError(
        "RIGHTS_CATALOG_STORAGE_UNAVAILABLE",
        "The rights catalog storage is temporarily unavailable.",
        retryable=True,
    )
