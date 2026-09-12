from pathlib import Path

from sqlalchemy import text
from tests.postgres import isolated_postgres_engine


async def test_current_sql_bootstraps_empty_schema_and_preserves_existing_cooldown():
    document = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as connection:
            schema = await connection.scalar(text("SELECT current_schema()"))
            assert schema.startswith("test_") and schema.replace("_", "").isalnum()
            # Full SQL creates every table in the first namespace. Public is
            # needed only to resolve the already-installed pgcrypto functions;
            # do not use SQLAlchemy create_all with this search_path.
            await connection.execute(text(f'SET search_path TO "{schema}", public'))
            await connection.commit()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(document)
            await driver.execute(
                "INSERT INTO provider_route_cooldowns "
                "(provider_key, access_policy_id, egress_binding_id, "
                "blocked_until, reason_code, version) "
                "VALUES ('youtube', 'public', 'controlled', "
                "now() + interval '10 minutes', 'provider_rate_limited', 7)"
            )
            await driver.execute(document)
            row = await driver.fetchrow(
                "SELECT version, blocked_until > now() AS blocked "
                "FROM provider_route_cooldowns"
            )
            assert row["version"] == 7 and row["blocked"] is True
            owner = await driver.fetchval(
                "SELECT table_schema FROM information_schema.tables "
                "WHERE table_name = 'provider_route_cooldowns' AND table_schema = $1",
                schema,
            )
            assert owner == schema
