from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml
from app.infrastructure.readiness import EXPECTED_DATABASE_TABLES

ROOT = Path(__file__).resolve().parents[2]
ENV_COMPOSE_PATH = ROOT.parent / "docker-compose-env.yml"
COMPOSE_PATH = ROOT.parent / "docker-compose.yml"
PROD_COMPOSE_PATH = ROOT.parent / "docker-compose-prod.yml"
ENV_EXAMPLE_PATH = ROOT.parent / ".env.example"
PROD_ENV_EXAMPLE_PATH = ROOT.parent / ".env.prod.example"
CORS_VALIDATOR_PATH = ROOT.parent / "scripts/validate-minio-cors.sh"
SCHEMA_PATH = ROOT / "sql/schema.sql"
ROOT_README_PATH = ROOT.parent / "README.md"
FRONTEND_README_PATH = ROOT.parent / "frontend/README.md"
STARTUP_SCRIPT_PATH = ROOT.parent / "scripts/restart-project.ps1"
DOCKERFILE_PATH = ROOT.parent / "Dockerfile"


def _service_block(document: str, service: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service)}:\n(.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)",
        document,
    )
    assert match is not None
    return match.group(1)


def _env_value(path: Path, name: str) -> str:
    match = re.search(
        rf"(?m)^{re.escape(name)}=(.+)$", path.read_text(encoding="utf-8")
    )
    assert match is not None
    return match.group(1)


def _assert_exact_http_origins(value: str) -> None:
    assert value
    assert "*" not in value
    assert "?" not in value
    for origin in value.split(","):
        parsed = urlsplit(origin)
        assert parsed.scheme in {"http", "https"}
        assert parsed.hostname is not None
        assert parsed.username is None
        assert parsed.password is None
        assert parsed.path == ""
        assert parsed.query == ""
        assert parsed.fragment == ""
        assert origin == f"{parsed.scheme}://{parsed.netloc}"
        _ = parsed.port


def test_environment_templates_do_not_override_duplicate_assignments() -> None:
    for path in (ENV_EXAMPLE_PATH, PROD_ENV_EXAMPLE_PATH):
        assignments = re.findall(
            r"(?m)^([A-Z][A-Z0-9_]*)=", path.read_text(encoding="utf-8")
        )
        assert len(assignments) == len(set(assignments))
        assert _env_value(path, "REQUEST_TIMEOUT_SECONDS") == "180"


def test_frontend_compose_receives_only_public_runtime_configuration() -> None:
    expected = {
        "BACKEND_ORIGIN",
        "HOSTNAME",
        "MINIO_PUBLIC_ENDPOINT",
        "MINIO_PUBLIC_SECURE",
        "NODE_ENV",
        "PORT",
        "SITE_URL",
    }
    for path in (COMPOSE_PATH, PROD_COMPOSE_PATH):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        frontend = document["services"]["frontend"]
        api = document["services"]["api"]

        assert "env_file" not in frontend
        local_only = {"MINIO_LOCAL_BROWSER_ENDPOINT", "MINIO_LOCAL_BROWSER_SECURE"}
        assert set(frontend["environment"]) == expected | local_only
        assert frontend["networks"]["app_net"]["ipv4_address"] == "10.251.0.10"
        assert "10.251.0.10/32" in api["environment"]["TRUSTED_PROXY_CIDRS"]


def test_production_analysis_is_opt_in() -> None:
    assert _env_value(PROD_ENV_EXAMPLE_PATH, "ANALYSIS_ENABLED") == "false"
    assert _env_value(PROD_ENV_EXAMPLE_PATH, "SCREENPLAY_ANALYSIS_ENABLED") == "false"


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
    assert schema.count("'video_article'") >= 2
    assert "to_jsonb('video_visual_analysis'::text)" in schema
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in schema
    assert "skill_instructions_sha256" in schema
    assert "digest(skill_instructions, 'sha256')" in schema
    assert "ck_analysis_jobs_skill_instructions_sha256" in schema
    assert "ALTER TABLE artifacts DROP COLUMN IF EXISTS expires_at" in schema
    assert "ALTER TABLE documents DROP COLUMN IF EXISTS expires_at" in schema
    assert "ALTER TABLE document_artifacts DROP COLUMN IF EXISTS expires_at" in schema
    assert (
        "ALTER TABLE analysis_report_artifacts DROP COLUMN IF EXISTS expires_at"
        in schema
    )
    assert (
        "ALTER TABLE analysis_jobs DROP COLUMN IF EXISTS retry_available_until"
        in schema
    )
    assert "('hongguo_web', '红果短剧官方分享', 230, TRUE, FALSE)" in schema
    assert "engine IN ('codex', 'claude', 'deepseek')" in schema
    assert "engine <> 'deepseek' OR auth_mode = 'api_key'" in schema
    assert "'local-codex', '本机 Codex', 'codex', 'host_login'" in schema
    assert "ck_ai_provider_local_codex_shape" in schema
    assert "ON CONFLICT (key) DO UPDATE SET" in schema
    assert "ADD COLUMN IF NOT EXISTS context_generation_id VARCHAR(64)" in schema
    assert "ALTER COLUMN context_generation_id SET NOT NULL" in schema
    assert "ix_provider_canary_target_generation_checked" in schema
    assert (
        "DROP INDEX IF EXISTS ix_provider_canary_target_profile_route_checked" in schema
    )


def test_ai_provider_selection_is_not_configured_by_environment() -> None:
    for path in (ENV_EXAMPLE_PATH, PROD_ENV_EXAMPLE_PATH):
        document = path.read_text(encoding="utf-8")
        assert "ANALYSIS_CLI_PROVIDER=" not in document
        assert "ANALYSIS_CODEX_MODEL=" not in document
        assert "ANALYSIS_CLAUDE_MODEL=" not in document


def test_compose_does_not_bundle_host_managed_infrastructure() -> None:
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
        assert not re.search(rf"(?m)^  {re.escape(service)}:$", compose)
    assert "profiles: [environment]" not in compose
    assert "/docker-entrypoint-initdb.d/" not in compose


def test_environment_bootstrap_provisions_analysis_storage_probe() -> None:
    compose = ENV_COMPOSE_PATH.read_text(encoding="utf-8")
    minio_init = _service_block(compose, "minio-init")

    assert (
        "image: minio/mc@sha256:"
        "a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727"
    ) in minio_init
    assert "mc mb --ignore-existing" in minio_init
    assert "system/analysis-readiness" in minio_init
    assert "mc pipe" in minio_init


def test_environment_minio_applies_exact_browser_cors_origins() -> None:
    compose = ENV_COMPOSE_PATH.read_text(encoding="utf-8")
    cors_check = _service_block(compose, "minio-config-check")
    minio = _service_block(compose, "minio")

    assert (
        "image: minio/minio@sha256:"
        "14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e"
    ) in minio
    expected_setting = (
        'MINIO_API_CORS_ALLOW_ORIGIN: "${MINIO_CORS_ALLOWED_ORIGINS-'
        'http://127.0.0.1:8101,http://localhost:8101}"'
    )
    assert expected_setting in cors_check
    assert expected_setting in minio
    assert "${MINIO_CORS_ALLOWED_ORIGINS:-" not in cors_check
    assert (
        'entrypoint: ["/bin/sh", "/opt/video-server/validate-minio-cors.sh"]'
        in cors_check
    )
    assert (
        "./scripts/validate-minio-cors.sh:/opt/video-server/validate-minio-cors.sh:ro"
    ) in cors_check
    assert "entrypoint:" not in minio
    assert "condition: service_completed_successfully" in minio
    assert 'command: ["minio", "server", "/data"' in minio
    assert "/bin/sh" not in minio
    assert "/usr/bin/docker-entrypoint.sh" not in minio

    for path in (ENV_EXAMPLE_PATH, PROD_ENV_EXAMPLE_PATH):
        _assert_exact_http_origins(_env_value(path, "MINIO_CORS_ALLOWED_ORIGINS"))


@pytest.mark.parametrize(
    "origins",
    (
        "",
        "*",
        "https://app.example.com/path",
        "https://user@app.example.com",
        "https://:443",
        "https://app.example.com:0",
        "https://app.example.com:70000",
        "https://bad_host.example.com",
    ),
)
@pytest.mark.skipif(os.name == "nt", reason="MinIO image validator is POSIX-only")
def test_minio_cors_validator_rejects_non_exact_origins(origins: str) -> None:
    result = subprocess.run(
        ["/bin/sh", str(CORS_VALIDATOR_PATH)],
        env={**os.environ, "MINIO_API_CORS_ALLOW_ORIGIN": origins},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 64


@pytest.mark.skipif(os.name == "nt", reason="MinIO image validator is POSIX-only")
def test_minio_cors_validator_accepts_exact_origin_list() -> None:
    result = subprocess.run(
        ["/bin/sh", str(CORS_VALIDATOR_PATH)],
        env={
            **os.environ,
            "MINIO_API_CORS_ALLOW_ORIGIN": (
                "https://app.example.com,http://127.0.0.1:8101"
            ),
        },
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_database_consumers_use_the_configured_postgres_service() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    expected_endpoint = (
        "@${POSTGRES_HOST:-host.docker.internal}:${POSTGRES_PORT:-5432}/"
    )

    for service in (
        "api",
        "outbox",
        "worker-download",
        "worker-import",
        "worker-report",
        "provider-canary",
    ):
        service_config = _service_block(compose, service)
        assert expected_endpoint in service_config
        assert '"host.docker.internal:host-gateway"' in service_config


def test_production_compose_uses_the_production_env_and_host_database() -> None:
    production = PROD_COMPOSE_PATH.read_text(encoding="utf-8")
    api = _service_block(production, "api")

    assert "env_file:\n      - .env.prod" in api
    assert "@${POSTGRES_HOST:-host.docker.internal}:${POSTGRES_PORT:-5432}/" in api
    assert not re.search(r"(?m)^  database-init:$", production)


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

    assert "env_file:\n      - .env" in api
    for variable in (
        "MEDIA_IMPORT_ENABLED",
        "DOCUMENT_IMPORT_ENABLED",
        "SCREENPLAY_ANALYSIS_ENABLED",
        "MEDIA_IMPORT_MAX_BYTES",
        "DOCUMENT_IMPORT_MAX_BYTES",
        "IMPORT_UPLOAD_SESSION_TTL_SECONDS",
        "IMPORT_UPLOAD_PART_SIZE_BYTES",
        "IMPORT_UPLOAD_MAX_PARTS",
        "IMPORT_UPLOAD_MAX_CONCURRENCY",
        "IMPORT_RIGHTS_STATEMENT_VERSION",
    ):
        assert variable not in api


def test_import_worker_is_private_bounded_and_uses_env_file_credentials() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    worker = _service_block(compose, "worker-import")

    assert "SERVICE_ROLE: import-worker" in worker
    assert "RABBITMQ_IMPORT_USER" in worker
    assert "RABBITMQ_IMPORT_PASS" in worker
    assert "env_file:\n      - .env" in worker
    assert "MINIO_IMPORT_ACCESS_KEY" not in worker
    assert "MINIO_IMPORT_SECRET_KEY" not in worker
    assert "networks:\n      - app_net" in worker
    assert "runner_egress_net" not in worker
    assert "ports:" not in worker
    assert 'command: ["python", "-m", "app.workers.imports.main"]' in worker


def test_compose_assigns_each_application_container_its_process_entrypoint() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    commands = {
        "api": "app.main",
        "outbox": "app.workers.outbox.main",
        "worker-download": "app.workers.download.main",
        "worker-import": "app.workers.imports.main",
        "worker-report": "app.workers.report.main",
        "provider-canary": "app.workers.canary.main",
    }

    for service, module in commands.items():
        service_config = _service_block(compose, service)
        assert f'command: ["python", "-m", "{module}"]' in service_config


def test_compose_waits_for_runner_and_api_dependency_readiness() -> None:
    for path in (COMPOSE_PATH, PROD_COMPOSE_PATH):
        compose = path.read_text(encoding="utf-8")
        api = _service_block(compose, "api")
        frontend = _service_block(compose, "frontend")
        runner = _service_block(compose, "media-runner")

        assert "media-runner:\n        condition: service_healthy" in api
        assert "127.0.0.1:8111/health/ready" in api
        assert "api:\n        condition: service_healthy" in frontend
        assert "127.0.0.1:8101/" in frontend
        assert "127.0.0.1:19100/health/ready" in runner


def test_project_documents_container_and_complete_local_entrypoints() -> None:
    root_readme = ROOT_README_PATH.read_text(encoding="utf-8")
    frontend_readme = FRONTEND_README_PATH.read_text(encoding="utf-8")
    compose_entrypoint = (
        "docker compose --env-file .env -f docker-compose.yml up -d --build "
        "--force-recreate --remove-orphans --wait --wait-timeout 300"
    )

    assert not STARTUP_SCRIPT_PATH.exists()
    assert not (ROOT.parent / "scripts/run-local-backend.py").exists()
    assert not (ROOT.parent / "scripts/start-local.sh").exists()
    assert not (ROOT.parent / "scripts/analysis-worker.sh").exists()
    assert not (ROOT / "app/workers/analysis/launchd.py").exists()
    assert compose_entrypoint in root_readme
    assert "run-local-backend.py" not in root_readme
    assert "run-local-backend.py" not in frontend_readme
    assert "restart-project.ps1" not in root_readme
    for action in ("doctor", "install", "status"):
        assert (
            f"uv run python -m app.workers.analysis.agent_cli {action}" in root_readme
        )


def test_runtime_dependency_install_is_cached_and_retried() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "target=/var/cache/apt,sharing=locked" in dockerfile
    assert "target=/var/lib/apt/lists,sharing=locked" in dockerfile
    assert "apt-get -o Acquire::Retries=5 update" in dockerfile
    assert "apt-get -o Acquire::Retries=5 install" in dockerfile


def test_compose_pins_shared_runner_workspace_to_the_mounted_container_path() -> None:
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    for service in (
        "media-runner",
        "worker-download",
        "youtube-operator-runner",
        "provider-operator-runner",
    ):
        service_config = _service_block(compose, service)
        assert "RUNNER_WORKSPACE_ROOT: /work" in service_config
        assert "RUNNER_WORKSPACE_ROOT:-" not in service_config
        assert "runner_work:/work" in service_config


def test_provider_session_runners_are_physically_isolated_by_provider() -> None:
    expected = {
        "douyin-operator-runner": ("douyin", "douyin-operator"),
        "xiaohongshu-operator-runner": ("xiaohongshu", "xiaohongshu-operator"),
        "reddit-operator-runner": ("reddit", "reddit-operator"),
        "x-operator-runner": ("x", "x-operator"),
        "instagram-operator-runner": ("instagram", "instagram-operator"),
    }

    for path in (COMPOSE_PATH, PROD_COMPOSE_PATH):
        compose = path.read_text(encoding="utf-8")
        for service, (provider, profile) in expected.items():
            service_config = _service_block(compose, service)
            assert f"profiles: [{profile}]" in service_config
            assert "<<: *provider-session-runner" in service_config
            assert "<<: *provider-session-environment" in service_config
            assert "runner_work:/work" in service_config
            assert f"target: /run/provider-secrets/{provider}" in service_config
            assert service_config.count("target: /run/provider-secrets/") == 1
            assert f'RUNNER_OPERATOR_SESSION_VERSIONS: \'{{"{provider}":' in (
                service_config
            )


def test_youtube_operator_mount_is_shared_by_compose_modes() -> None:
    compose_documents = (
        COMPOSE_PATH.read_text(encoding="utf-8"),
        PROD_COMPOSE_PATH.read_text(encoding="utf-8"),
    )

    for document in compose_documents:
        youtube_operator = _service_block(document, "youtube-operator-runner")
        assert "RUNNER_YOUTUBE_COOKIE_SYNC_ROOT: /run/youtube-cookie-sync" in (
            youtube_operator
        )
        assert (
            'source: "${YOUTUBE_COOKIE_SYNC_DIR:-${HOME}/Library/Caches/'
            'FrameFetch/youtube-cookie-sync}"' in youtube_operator
        )
        assert "target: /run/youtube-cookie-sync" in youtube_operator
        assert "read_only: false" in youtube_operator
        assert "create_host_path: false" in youtube_operator
        assert document.count("RUNNER_YOUTUBE_COOKIE_SYNC_ROOT") == 1
        assert document.count("target: /run/youtube-cookie-sync") == 1

    assert "YOUTUBE_COOKIE_SYNC_DIR=\n" in ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    assert "YOUTUBE_COOKIE_SYNC_DIR=\n" in PROD_ENV_EXAMPLE_PATH.read_text(
        encoding="utf-8"
    )
    assert _env_value(ENV_EXAMPLE_PATH, "YOUTUBE_COOKIE_VERSION") == "chrome-default"
    assert _env_value(PROD_ENV_EXAMPLE_PATH, "YOUTUBE_COOKIE_SECRET_DIR") == (
        "./.provider-secrets/youtube"
    )


def test_wechat_channels_is_anonymous_only_without_browser_session_runtime() -> None:
    compose_documents = (
        COMPOSE_PATH.read_text(encoding="utf-8"),
        PROD_COMPOSE_PATH.read_text(encoding="utf-8"),
    )

    assert not (ROOT.parent / "scripts/authorize-provider-session.sh").exists()
    assert not (ROOT.parent / "scripts/provider-session-broker.sh").exists()
    assert not (ROOT / "app/runner/provider_session_broker.py").exists()
    assert not (ROOT / "app/runner/provider_session_launchd.py").exists()
    assert not (ROOT / "app/runner/provider_session_authorize.py").exists()
    assert not (ROOT / "app/runner/managed_chrome_session.py").exists()
    assert not (ROOT / "app/runner/managed_chrome_cdp.py").exists()
    assert not (ROOT / "app/runner/managed_session_cookies.py").exists()
    assert not (ROOT / "app/runner/browser_cookie_export.py").exists()
    assert not (ROOT / "app/runner/browser_cookie_source.py").exists()
    for compose in compose_documents:
        assert "wechat-channels-operator-runner" not in compose
        assert "wechat-channels-operator" not in compose
        assert "WECHAT_CHANNELS_COOKIE_" not in compose
        assert "RUNNER_PROVIDER_SESSION_ACQUISITION" not in compose
