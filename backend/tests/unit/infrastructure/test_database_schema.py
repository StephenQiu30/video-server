from datetime import UTC, datetime

from app.infrastructure.database import Base
from app.infrastructure.database.artifact_repository import expired_artifact_statement
from app.infrastructure.database.outbox_repository import outbox_claim_statement
from app.infrastructure.database.recovery_repository import stale_jobs_statement
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable


def test_download_schema_contains_required_tables_and_columns() -> None:
    tables = Base.metadata.tables
    assert {
        "artifacts",
        "auth_sessions",
        "download_jobs",
        "media_formats",
        "media_inspections",
        "outbox_events",
        "users",
    } <= set(tables)
    jobs = tables["download_jobs"]
    assert {
        "status",
        "stage",
        "progress",
        "attempt",
        "version",
        "lease_owner",
        "lease_expires_at",
        "heartbeat_at",
        "semantic_plan",
    } <= set(jobs.columns.keys())
    assert jobs.c.semantic_plan.type.compile(postgresql.dialect()) == "JSONB"
    assert {
        "username",
        "normalized_username",
        "email",
        "password_hash",
        "role",
        "is_active",
    } <= set(tables["users"].columns.keys())
    assert {"user_id", "token_hash", "expires_at"} <= set(
        tables["auth_sessions"].columns.keys()
    )


def test_sensitive_url_is_not_a_plaintext_column() -> None:
    inspection = Base.metadata.tables["media_inspections"]
    assert "url" not in inspection.columns
    assert {"url_ciphertext", "url_nonce", "url_key_id"} <= set(
        inspection.columns.keys()
    )
    ddl = str(CreateTable(inspection).compile(dialect=postgresql.dialect()))
    assert "BYTEA" in ddl


def test_constraints_cover_idempotency_progress_and_artifact_identity() -> None:
    dialect = postgresql.dialect()
    job_ddl = str(
        CreateTable(Base.metadata.tables["download_jobs"]).compile(dialect=dialect)
    )
    artifact_ddl = str(
        CreateTable(Base.metadata.tables["artifacts"]).compile(dialect=dialect)
    )
    user_ddl = str(CreateTable(Base.metadata.tables["users"]).compile(dialect=dialect))
    assert "uq_download_jobs_owner_idempotency" in job_ddl
    assert "progress BETWEEN 0 AND 100" in job_ddl
    assert "uq_artifacts_job" in artifact_ddl
    assert "uq_artifacts_object" in artifact_ddl
    assert "ck_users_role" in user_ddl


def test_postgres_claims_use_skip_locked_for_parallel_consumers() -> None:
    now = datetime(2026, 8, 6, tzinfo=UTC)
    dialect = postgresql.dialect()
    stale_sql = str(stale_jobs_statement(now, 10).compile(dialect=dialect))
    outbox_sql = str(outbox_claim_statement(now, 10).compile(dialect=dialect))
    artifact_sql = str(expired_artifact_statement(now, 10).compile(dialect=dialect))
    assert "FOR UPDATE SKIP LOCKED" in stale_sql
    assert "FOR UPDATE SKIP LOCKED" in outbox_sql
    assert "FOR UPDATE SKIP LOCKED" in artifact_sql
    assert "NOT (EXISTS" in artifact_sql
