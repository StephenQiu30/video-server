from __future__ import annotations

from app.infrastructure.database import Base
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable


def test_analysis_schema_has_jobs_runs_results_and_runtime_retention_locks() -> None:
    tables = Base.metadata.tables
    assert {
        "analysis_jobs",
        "analysis_runs",
        "analysis_retry_operations",
        "analysis_report_versions",
        "analysis_report_artifacts",
        "analysis_artifact_locks",
        "task_events",
    } <= set(tables)
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
        "active_run_id",
        "current_run_no",
        "current_run_trigger",
        "current_report_id",
    } <= set(jobs.columns.keys())
    ddl = str(CreateTable(jobs).compile(dialect=postgresql.dialect()))
    assert "uq_analysis_jobs_owner_idempotency" in ddl
    assert "progress BETWEEN 0 AND 100" in ddl
    runs = tables["analysis_runs"]
    assert {"job_id", "run_no", "trigger", "attempt", "version"} <= set(
        runs.columns.keys()
    )


def test_result_is_strict_jsonb_without_transcript_or_provider_payload_columns() -> (
    None
):
    result = Base.metadata.tables["analysis_report_versions"]
    assert result.c.result_json.type.compile(postgresql.dialect()) == "JSONB"
    assert "transcript" not in result.columns
    assert "provider_response" not in result.columns
    assert {"provider", "model", "cli_version"} <= set(result.columns.keys())
    assert "run_id" in result.columns
    assert {"report_markdown", "content_sha256", "renderer_version", "status"} <= set(
        result.columns.keys()
    )
    assert {"schema_version", "prompt_version"}.isdisjoint(result.columns)
    ddl = str(CreateTable(result).compile(dialect=postgresql.dialect()))
    assert "jsonb_typeof(result_json) = 'object'" in ddl
