"""Transactional PostgreSQL rights-catalog boundary."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine

from video_server.errors import DomainError
from video_server.source.rights import RightsCatalog


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
        raise NotImplementedError
