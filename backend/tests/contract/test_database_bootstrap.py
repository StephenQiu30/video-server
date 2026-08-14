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
    assert "ck_download_jobs_source_shape" in schema
    assert "ck_media_imports_terminal_shape" in schema
    assert "ck_media_import_attempts_verifying_shape" in schema
    assert "ck_media_import_attempts_terminal_shape" in schema
    assert "ck_documents_ready_shape" in schema
    assert "ck_document_import_attempts_terminal_shape" in schema
    assert "ck_document_artifacts_deleted_shape" in schema
    assert "fk_analysis_jobs_document" in schema
    assert "ck_analysis_jobs_input_shape" in schema
    assert "SET source_kind = 'remote_provider'" in schema
    assert "result_contract = COALESCE(" in schema
    assert "ck_analysis_report_versions_result_kind" in schema
    assert "result_json ? 'kind'" in schema
    assert "to_jsonb('video_visual_analysis'::text)" in schema
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in schema
    assert "skill_instructions_sha256" in schema
    assert "digest(skill_instructions, 'sha256')" in schema
    assert "ck_analysis_jobs_skill_instructions_sha256" in schema
    assert "created_at + INTERVAL '7 days'" in schema
    assert "expires_at <= created_at + INTERVAL '25 hours'" in schema


def test_optional_environment_services_use_one_profile() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    for service in (
        "postgres",
        "database-init",
        "rabbitmq",
        "rabbitmq-init",
        "valkey",
        "minio",
        "minio-init",
    ):
        service_config = _service_block(compose, service)
        assert "profiles: [environment]" in service_config


def test_compose_initializes_database_before_database_consumers_start() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    initializer = _service_block(compose, "database-init")

    assert "psql" in initializer
    assert "/schema/schema.sql" in initializer
    assert "postgres:\n        condition: service_healthy" in initializer
    assert "/docker-entrypoint-initdb.d/" not in compose


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


def test_compose_uses_typed_application_retention_defaults() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    production = PROD_COMPOSE_PATH.read_text(encoding="utf-8")

    for variable in (
        "ARTIFACT_TTL_SECONDS",
        "ARTIFACT_GC_INTERVAL_SECONDS",
        "ARTIFACT_GC_BATCH_SIZE",
        "ARTIFACT_DELETE_TIMEOUT_SECONDS",
        "ARTIFACT_DOWNLOAD_URL_TTL_SECONDS",
        "ANALYSIS_REPORT_TTL_SECONDS",
        "ANALYSIS_REPORT_GC_INTERVAL_SECONDS",
        "ANALYSIS_REPORT_GC_BATCH_SIZE",
        "ANALYSIS_REPORT_ORPHAN_GRACE_SECONDS",
    ):
        assert variable not in compose
        assert variable not in production


def test_api_receives_feature_flags_and_uses_typed_import_defaults() -> None:
    api = _service_block(COMPOSE_PATH.read_text(encoding="utf-8"), "api")

    assert 'MEDIA_IMPORT_ENABLED: "${MEDIA_IMPORT_ENABLED:-false}"' in api
    assert 'DOCUMENT_IMPORT_ENABLED: "${DOCUMENT_IMPORT_ENABLED:-false}"' in api
    assert 'SCREENPLAY_ANALYSIS_ENABLED: "${SCREENPLAY_ANALYSIS_ENABLED:-false}"' in api
    for variable in (
        "MEDIA_IMPORT_MAX_BYTES",
        "DOCUMENT_IMPORT_MAX_BYTES",
        "IMPORT_UPLOAD_SESSION_TTL_SECONDS",
        "IMPORT_UPLOAD_PART_SIZE_BYTES",
        "IMPORT_UPLOAD_MAX_PARTS",
        "IMPORT_UPLOAD_MAX_CONCURRENCY",
        "IMPORT_RIGHTS_STATEMENT_VERSION",
    ):
        assert variable not in api


def test_import_worker_is_private_bounded_and_uses_dedicated_identities() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    worker = _service_block(compose, "worker-import")

    assert "SERVICE_ROLE: import-worker" in worker
    assert "RABBITMQ_IMPORT_URL" in worker
    assert "MINIO_IMPORT_ACCESS_KEY" in worker
    assert "MINIO_IMPORT_SECRET_KEY" in worker
    assert "networks: [db_net, queue_net, storage_net]" in worker
    assert "public_egress_net" not in worker
    assert 'command: ["python", "-m", "app.workers.imports.main"]' in worker
    assert "read_only: true" in worker
    assert "cap_drop: [ALL]" in worker
    assert "security_opt: [no-new-privileges:true]" in worker
    assert "pids_limit: 128" in worker
    assert "/work:rw,noexec,nosuid,size=3g" in worker


def test_compose_pins_shared_runner_workspace_to_the_mounted_container_path() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    for service in (
        "api",
        "worker-download",
        "provider-canary",
        "media-runner",
        "youtube-operator-runner",
        "provider-operator-runner",
    ):
        service_config = _service_block(compose, service)
        assert "RUNNER_WORKSPACE_ROOT: /work" in service_config
        assert "RUNNER_WORKSPACE_ROOT:-" not in service_config
