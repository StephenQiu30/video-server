"""Shared SQLAlchemy declarative metadata."""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

_RAW_DDL_TABLES = frozenset(
    {
        "rights_statement_catalog",
        "jobs",
        "source_resolution_requests",
        "job_events",
        "outbox_messages",
    }
)


class Base(DeclarativeBase):
    """Declarative base used by models and migration drift checks."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def include_managed_object(
    object_: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Exclude frozen raw-DDL tables from ORM metadata drift operations."""

    del object_
    return not (type_ == "table" and reflected and compare_to is None and name in _RAW_DDL_TABLES)
