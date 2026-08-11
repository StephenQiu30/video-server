from __future__ import annotations

import re
from pathlib import Path

from app.infrastructure.readiness import EXPECTED_DATABASE_TABLES

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT.parent / "docker-compose.yml"
PROD_COMPOSE_PATH = ROOT.parent / "docker-compose-prod.yml"
SCHEMA_PATH = ROOT / "sql/schema.sql"


def _service_block(document: str, service: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service)}:\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)",
        document,
    )
    assert match is not None
    return match.group(1)


def test_current_schema_can_be_applied_repeatedly() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    table_names = set(
        re.findall(r"^CREATE TABLE IF NOT EXISTS ([a-z_]+)", schema, re.MULTILINE)
    )

    assert table_names == EXPECTED_DATABASE_TABLES
    assert not re.search(r"^CREATE TABLE (?!IF NOT EXISTS)", schema, re.MULTILINE)
    assert not re.search(r"^CREATE INDEX (?!IF NOT EXISTS)", schema, re.MULTILINE)
    assert "analysis_report_unavailable" in schema
    assert "ck_analysis_jobs_succeeded_report" in schema
    assert "ix_download_jobs_queued_recovery" in schema


def test_compose_initializes_database_before_database_consumers_start() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    initializer = _service_block(compose, "database-init")

    assert "psql" in initializer
    assert "/schema/schema.sql" in initializer
    assert "postgres:\n        condition: service_healthy" in initializer
    assert "/docker-entrypoint-initdb.d/" not in compose

    for service in ("api", "outbox", "worker-download", "provider-canary"):
        service_config = _service_block(compose, service)
        assert (
            "database-init:\n        condition: service_completed_successfully"
            in service_config
        )


def test_production_compose_requires_database_initializer_credentials() -> None:
    initializer = _service_block(
        PROD_COMPOSE_PATH.read_text(encoding="utf-8"), "database-init"
    )

    assert 'POSTGRES_DB: "${POSTGRES_DB:?set POSTGRES_DB in .env.prod}"' in initializer
    assert (
        'POSTGRES_USER: "${POSTGRES_USER:?set POSTGRES_USER in .env.prod}"'
        in initializer
    )
    assert (
        'POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env.prod}"'
        in initializer
    )
