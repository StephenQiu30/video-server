"""SQLAlchemy declarative base shared by the API, Worker and Alembic."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application metadata root.

    Models are imported by Alembic before ``Base.metadata`` is inspected.  No
    table is created at runtime; schema changes are owned by Alembic.
    """
