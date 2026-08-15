from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://video:video@127.0.0.1:5432/video"
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        extra="ignore",
        case_sensitive=False,
    )

    test_database_url: str | None = None
    database_url: str = DEFAULT_TEST_DATABASE_URL

    @property
    def resolved_url(self) -> str:
        return self.test_database_url or self.database_url


@asynccontextmanager
async def isolated_postgres_engine() -> AsyncIterator[AsyncEngine]:
    database_url = TestDatabaseSettings().resolved_url
    if make_url(database_url).drivername != "postgresql+asyncpg":
        raise RuntimeError("TEST_DATABASE_URL must use postgresql+asyncpg")
    schema = f"test_{uuid4().hex}"
    admin = create_async_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(CreateSchema(schema))
        engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            # Do not fall back to public: SQLAlchemy's table-existence probe
            # follows search_path and would otherwise reuse deployment tables.
            connect_args={"server_settings": {"search_path": schema}},
        )
        try:
            yield engine
        finally:
            await engine.dispose()
    finally:
        async with admin.connect() as connection:
            await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        await admin.dispose()
