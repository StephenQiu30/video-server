from pathlib import Path

from sqlalchemy import text
from tests.postgres import isolated_postgres_engine


async def test_source_schema_bootstrap_and_repeat_keep_revocation() -> None:
    sql = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as connection:
            schema = await connection.scalar(text("SELECT current_schema()"))
            assert schema.startswith("test_") and schema.replace("_", "").isalnum()
            await connection.execute(text(f'SET search_path TO "{schema}", public'))
            await connection.commit()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(sql)
            await driver.execute(
                "INSERT INTO provider_session_sources "
                "(provider_key, revision, ciphertext, valid_until, updated_at) "
                "VALUES ('youtube', 7, NULL, NULL, now())"
            )
            await driver.execute(sql)
            row = await driver.fetchrow("SELECT * FROM provider_session_sources")
            assert row["revision"] == 7 and row["ciphertext"] is None
