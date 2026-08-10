from __future__ import annotations

from app.infrastructure.database import Base
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable


def test_analysis_schema_has_jobs_results_and_runtime_retention_locks() -> None:
    tables = Base.metadata.tables
    assert {"analysis_jobs", "analysis_results", "analysis_artifact_locks"} <= set(
        tables
    )
    jobs = tables["analysis_jobs"]
    assert {
        "artifact_id",
        "input_sha256",
        "skill_id",
        "skill_instructions",
        "output_language",
        "attempt",
        "version",
        "lease_owner",
        "lease_expires_at",
    } <= set(jobs.columns.keys())
    ddl = str(CreateTable(jobs).compile(dialect=postgresql.dialect()))
    assert "uq_analysis_jobs_owner_idempotency" in ddl
    assert "progress BETWEEN 0 AND 100" in ddl


def test_result_is_strict_jsonb_without_transcript_or_provider_payload_columns() -> (
    None
):
    result = Base.metadata.tables["analysis_results"]
    assert result.c.result_json.type.compile(postgresql.dialect()) == "JSONB"
    assert "transcript" not in result.columns
    assert "provider_response" not in result.columns
    assert {"provider", "model", "cli_version"} <= set(result.columns.keys())
    assert {"schema_version", "prompt_version"}.isdisjoint(result.columns)
    ddl = str(CreateTable(result).compile(dialect=postgresql.dialect()))
    assert "jsonb_typeof(result_json) = 'object'" in ddl
