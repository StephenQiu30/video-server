from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

DEFAULT_TEST_DATABASE_URL = "postgresql+asyncpg://video:video@127.0.0.1:15432/video"


@asynccontextmanager
async def isolated_postgres_engine() -> AsyncIterator[AsyncEngine]:
    database_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
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
