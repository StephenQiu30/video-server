from pathlib import Path

from sqlalchemy import text
from tests.postgres import isolated_postgres_engine


async def test_avatar_columns_converge_on_existing_schema() -> None:
    sql = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as connection:
            schema = await connection.scalar(text("SELECT current_schema()"))
            assert schema and schema.startswith("test_")
            await connection.execute(text(f'SET search_path TO "{schema}", public'))
            await connection.commit()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(sql)
            await driver.execute(
                "ALTER TABLE users DROP COLUMN avatar_data, DROP COLUMN avatar_version"
            )
            await driver.execute(sql)
            await driver.execute(sql)
            columns = await driver.fetch(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = $1 AND table_name = 'users' "
                "AND column_name IN ('avatar_data', 'avatar_version')",
                schema,
            )
    assert {row["column_name"]: row["data_type"] for row in columns} == {
        "avatar_data": "bytea",
        "avatar_version": "uuid",
    }
