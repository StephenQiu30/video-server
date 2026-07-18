"""Fresh PostgreSQL migration fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from testcontainers.postgres import PostgresContainer

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_POSTGRES_IMAGE = (
    "postgres:17-alpine@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"
)


def _psycopg_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    raise ValueError("VIDEO_TEST_DSN must be a PostgreSQL URL")


def _alembic_config(database_url: str) -> Config:
    config = Config(str(_PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    external_url = os.environ.get("VIDEO_TEST_DSN")
    if external_url is not None:
        database_url = _psycopg_url(external_url)
        database_name = make_url(database_url).database
        if database_name is None or not database_name.endswith("_test"):
            raise ValueError("VIDEO_TEST_DSN must name a dedicated database ending in _test")
        yield database_url
        return

    with PostgresContainer(_POSTGRES_IMAGE, driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def alembic_config(postgres_url: str) -> Config:
    return _alembic_config(postgres_url)


@pytest.fixture
def migrated_database(alembic_config: Config, postgres_url: str) -> Iterator[Engine]:
    config = alembic_config
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(postgres_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
