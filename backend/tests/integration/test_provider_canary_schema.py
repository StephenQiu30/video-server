from pathlib import Path

from sqlalchemy import text
from tests.postgres import isolated_postgres_engine


async def test_canary_schema_accepts_guest_and_preserves_evidence_on_reapply():
    document = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as connection:
            schema = await connection.scalar(text("SELECT current_schema()"))
            assert schema.startswith("test_") and schema.replace("_", "").isalnum()
            await connection.execute(text(f'SET search_path TO "{schema}", public'))
            await connection.commit()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(document)
            for mode in ("anonymous", "guest", "operator_managed"):
                await driver.execute(
                    "INSERT INTO provider_canary_results "
                    "(id, target_id, provider_key, profile_version, "
                    "stage, access_mode, "
                    "outcome, duration_ms, engine_commit, egress_affinity_id, "
                    "client_profile_id, context_generation_id) "
                    "VALUES (gen_random_uuid(), 'owned', 'douyin', 'douyin-public', "
                    "'media', $1, 'succeeded', 100, 'commit', 'egress', 'client', $1)",
                    mode,
                )
            await driver.execute(document)
            assert (
                await driver.fetchval("SELECT count(*) FROM provider_canary_results")
                == 3
            )
            modes = await driver.fetch(
                "SELECT access_mode FROM provider_canary_results"
            )
            assert {row["access_mode"] for row in modes} == {
                "anonymous",
                "guest",
                "operator_managed",
            }
