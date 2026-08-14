from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import DEFAULT_URL_ENCRYPTION_KEY, Settings
from pydantic import SecretStr, ValidationError


def test_settings_resolve_frontend_dist_from_repository_root() -> None:
    settings = Settings(app_env="test")

    assert settings.frontend_dist_dir.name == "out"
    assert settings.frontend_dist_dir.parent.name == "frontend"


def test_explicit_frontend_dist_is_resolved(tmp_path: Path) -> None:
    settings = Settings(app_env="test", frontend_dist_dir=tmp_path / "web")

    assert settings.frontend_dist_dir == (tmp_path / "web").resolve()


def test_relative_frontend_dist_is_resolved_from_repository() -> None:
    settings = Settings(app_env="test", frontend_dist_dir=Path("custom-ui"))

    assert settings.frontend_dist_dir.is_absolute()
    assert settings.frontend_dist_dir.name == "custom-ui"


def test_port_bounds_are_validated() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="test", app_port=0)


@pytest.mark.parametrize(
    "field",
    ("database_url", "analysis_database_url"),
)
def test_database_urls_require_async_postgresql(field: str) -> None:
    with pytest.raises(ValidationError, match=r"postgresql\+asyncpg"):
        Settings(app_env="test", _env_file=None, **{field: "sqlite:///video.db"})


def test_download_limits_are_validated() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="test", max_file_size_bytes=0)

    with pytest.raises(ValidationError):
        Settings(app_env="test", download_timeout_seconds=0)

    with pytest.raises(ValidationError):
        Settings(app_env="test", download_worker_threads=0)


def test_local_imports_are_bounded_and_disabled_by_default() -> None:
    settings = Settings(app_env="test", _env_file=None)

    assert settings.media_import_enabled is False
    assert settings.document_import_enabled is False
    assert settings.screenplay_analysis_enabled is False
    assert settings.analysis_max_screenplay_bytes == 2 * 1024**2
    assert settings.analysis_screenplay_rewrite_chunk_characters == 8_000
    assert settings.analysis_max_screenplay_rewrite_chunks == 128
    assert settings.analysis_screenplay_rewrite_context_characters == 1_000
    assert settings.analysis_max_screenplay_rewrite_output_characters == 400_000
    assert settings.analysis_screenplay_rewrite_chunk_call_attempts == 2
    assert settings.analysis_screenplay_rewrite_chunk_retry_delay_seconds == 1.0
    assert settings.media_import_max_bytes == 2 * 1024**3
    assert settings.document_import_max_bytes == 50 * 1024**2
    assert settings.import_upload_session_ttl_seconds == 900
    assert settings.import_upload_part_size_bytes == 32 * 1024**2
    assert settings.import_upload_max_parts == 1000
    assert settings.import_upload_max_concurrency == 4
    assert settings.import_quarantine_retention_days == 1
    assert settings.import_rights_statement_version == "content-rights-v1"
    assert settings.import_ffprobe_timeout_seconds == 30
    assert settings.import_max_probe_output_bytes == 256 * 1024
    assert settings.import_max_video_width == 8192
    assert settings.import_max_video_height == 8192
    assert settings.import_max_media_streams == 32
    assert settings.import_recovery_batch_size == 50
    assert settings.import_workspace_grace_seconds == 1800
    assert settings.import_artifact_orphan_grace_seconds == 3600

    for field in (
        "media_import_max_bytes",
        "document_import_max_bytes",
        "import_upload_session_ttl_seconds",
        "import_upload_part_size_bytes",
        "import_upload_max_parts",
        "import_upload_max_concurrency",
        "import_quarantine_retention_days",
        "import_ffprobe_timeout_seconds",
        "import_max_probe_output_bytes",
        "import_max_video_width",
        "import_max_video_height",
        "import_max_media_streams",
        "import_recovery_interval_seconds",
        "import_recovery_batch_size",
        "import_workspace_grace_seconds",
        "import_artifact_orphan_grace_seconds",
    ):
        with pytest.raises(ValidationError):
            Settings(app_env="test", _env_file=None, **{field: 0})

    with pytest.raises(ValidationError):
        Settings(
            app_env="test",
            _env_file=None,
            import_rights_statement_version="Invalid Rights Version",
        )


def test_local_import_limit_must_fit_multipart_budget() -> None:
    with pytest.raises(ValidationError, match="multipart budget"):
        Settings(
            app_env="test",
            _env_file=None,
            media_import_max_bytes=20 * 1024**3,
            import_upload_part_size_bytes=5 * 1024**2,
            import_upload_max_parts=1000,
        )


def test_minio_public_endpoint_is_safe_for_browser_policy() -> None:
    settings = Settings(
        app_env="test",
        minio_public_endpoint="storage.example.com:9443",
        minio_public_secure=True,
        _env_file=None,
    )

    assert settings.minio_public_origin() == "https://storage.example.com:9443"
    for endpoint in (
        "https://storage.example.com",
        "storage.example.com/path",
        "storage.example.com;script-src",
    ):
        with pytest.raises(ValidationError, match="MINIO_PUBLIC_ENDPOINT"):
            Settings(
                app_env="test",
                minio_public_endpoint=endpoint,
                _env_file=None,
            )


def test_import_worker_runtime_limits_are_relationally_safe() -> None:
    with pytest.raises(ValidationError, match="heartbeat interval"):
        Settings(
            app_env="test",
            _env_file=None,
            job_lease_seconds=30,
            heartbeat_interval_seconds=30,
        )
    with pytest.raises(ValidationError, match="workspace grace"):
        Settings(
            app_env="test",
            _env_file=None,
            job_lease_seconds=60,
            import_workspace_grace_seconds=60,
        )


def test_production_import_worker_accepts_only_explicit_dedicated_credentials() -> None:
    settings = Settings(
        app_env="production",
        service_role="import-worker",
        database_url="postgresql+asyncpg://imports:StrongDb@postgres:5432/video",
        rabbitmq_url="amqp://imports:StrongMq@rabbitmq:5672/video",
        minio_import_access_key=SecretStr("production-import-access"),
        minio_import_secret_key=SecretStr("i" * 48),
        url_encryption_key=SecretStr("MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="),
        _env_file=None,
    )

    assert settings.service_role == "import-worker"


def test_user_artifacts_default_to_seven_days_and_allow_thirty_days() -> None:
    defaults = Settings(app_env="test", _env_file=None)
    seven_days = 7 * 24 * 60 * 60
    thirty_days = 30 * 24 * 60 * 60
    configured = Settings(
        app_env="test",
        artifact_ttl_seconds=thirty_days,
        analysis_report_ttl_seconds=thirty_days,
        _env_file=None,
    )

    assert defaults.artifact_ttl_seconds == seven_days
    assert defaults.analysis_report_ttl_seconds == seven_days
    assert configured.artifact_ttl_seconds == thirty_days
    assert configured.analysis_report_ttl_seconds == thirty_days
    with pytest.raises(ValidationError):
        Settings(app_env="test", artifact_ttl_seconds=86_400, _env_file=None)
    with pytest.raises(ValidationError):
        Settings(app_env="test", analysis_report_ttl_seconds=86_400, _env_file=None)


def test_signing_secrets_require_adequate_entropy_capacity() -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(app_env="test", auth_jwt_secret=SecretStr("too-short"))


def test_provider_release_approvals_are_typed_keys() -> None:
    settings = Settings(
        app_env="test", provider_verified_keys=frozenset({"tiktok", "vimeo"})
    )

    assert settings.provider_verified_keys == frozenset({"tiktok", "vimeo"})
    with pytest.raises(ValidationError, match="invalid key"):
        Settings(app_env="test", provider_verified_keys=frozenset({"VK Clips"}))


def test_peertube_allowlist_accepts_only_exact_domain_names() -> None:
    settings = Settings(
        app_env="test",
        peertube_allowed_instances=frozenset({"VIDEO.EXAMPLE.COM"}),
    )

    assert settings.peertube_allowed_instances == frozenset({"video.example.com"})
    for invalid in ("*.example.com", "https://video.example.com", "127.0.0.1"):
        with pytest.raises(ValidationError, match="invalid host"):
            Settings(app_env="test", peertube_allowed_instances=frozenset({invalid}))


def test_operator_runner_endpoints_are_provider_keyed_internal_urls() -> None:
    settings = Settings(
        app_env="test",
        runner_operator_base_urls={
            "youtube": "http://youtube-operator-runner:19100/",
            "tiktok": "http://provider-operator-runner:19100",
        },
    )

    assert settings.runner_operator_base_urls == {
        "youtube": "http://youtube-operator-runner:19100",
        "tiktok": "http://provider-operator-runner:19100",
    }
    for invalid in (
        {"TikTok": "http://provider-operator-runner:19100"},
        {"tiktok": "https://public.example/runner"},
        {"tiktok": "http://user:pass@provider-operator-runner:19100"},
    ):
        with pytest.raises(ValidationError, match="runner operator"):
            Settings(app_env="test", runner_operator_base_urls=invalid)


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_bootstrap_admin_email_is_normalized_to_none(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("AUTH_BOOTSTRAP_ADMIN_EMAIL", value)

    settings = Settings(app_env="test")

    assert settings.auth_bootstrap_admin_email is None


def test_bootstrap_admin_email_retains_email_validation() -> None:
    settings = Settings(app_env="test", auth_bootstrap_admin_email="admin@example.com")

    assert settings.auth_bootstrap_admin_email == "admin@example.com"
    with pytest.raises(ValidationError):
        Settings(app_env="test", auth_bootstrap_admin_email="not-an-email")


def test_production_rejects_development_secrets() -> None:
    with pytest.raises(ValidationError, match="production secrets"):
        Settings(app_env="production")


def test_production_accepts_explicit_secrets() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://app:StrongDbPass123@postgres:5432/video",
        rabbitmq_url="amqp://app:StrongMqPass123@rabbitmq:5672/",
        valkey_url="redis://valkey:6379/0",
        auth_jwt_secret=SecretStr("s" * 48),
        request_fingerprint_secret=SecretStr("f" * 48),
        url_encryption_key=SecretStr("MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="),
        runner_hmac_secret=SecretStr("r" * 48),
        minio_access_key=SecretStr("production-access"),
        minio_secret_key=SecretStr("m" * 48),
        minio_import_access_key=SecretStr("production-import-access"),
        minio_import_secret_key=SecretStr("i" * 48),
        metrics_access_key=SecretStr("k" * 48),
        auth_bootstrap_admin_email="admin@example.com",
        analysis_enabled=True,
    )

    assert settings.app_env == "production"
    assert settings.analysis_enabled is True


def test_production_rejects_default_url_encryption_key() -> None:
    with pytest.raises(ValidationError, match="production secrets"):
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://app:db-secret@postgres:5432/video",
            rabbitmq_url="amqp://app:mq-secret@rabbitmq:5672/",
            auth_jwt_secret=SecretStr("s" * 48),
            request_fingerprint_secret=SecretStr("f" * 48),
            runner_hmac_secret=SecretStr("r" * 48),
            minio_access_key=SecretStr("production-access"),
            minio_secret_key=SecretStr("m" * 48),
            analysis_enabled=True,
        )


def test_production_canary_requires_dedicated_storage_credentials() -> None:
    settings = Settings(
        app_env="production",
        service_role="provider-canary",
        database_url="postgresql+asyncpg://canary:StrongDbPass@postgres:5432/video",
        runner_hmac_secret=SecretStr("r" * 48),
        url_encryption_key=SecretStr("MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="),
        minio_access_key=SecretStr("canary-read-access"),
        minio_secret_key=SecretStr("m" * 48),
    )

    assert settings.service_role == "provider-canary"
    with pytest.raises(ValidationError, match="production secrets"):
        Settings(
            app_env="production",
            service_role="provider-canary",
            database_url=(
                "postgresql+asyncpg://canary:StrongDbPass@postgres:5432/video"
            ),
            runner_hmac_secret=SecretStr("r" * 48),
            url_encryption_key=SecretStr(
                "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
            ),
            _env_file=None,
        )


@pytest.mark.parametrize(
    "role",
    (
        "api",
        "outbox",
        "download-worker",
        "analysis-worker",
        "report-worker",
        "provider-canary",
    ),
)
def test_production_rejects_default_url_key_for_every_role(role: str) -> None:
    kwargs: dict[str, object] = {
        "app_env": "production",
        "service_role": role,
        "database_url": "postgresql+asyncpg://app:db-secret@postgres:5432/video",
    }
    if role in {"api", "outbox", "download-worker"}:
        kwargs["rabbitmq_url"] = "amqp://app:mq-secret@rabbitmq:5672/"
        kwargs["auth_jwt_secret"] = SecretStr("s" * 48)
        kwargs["request_fingerprint_secret"] = SecretStr("f" * 48)
        kwargs["runner_hmac_secret"] = SecretStr("r" * 48)
        kwargs["minio_access_key"] = SecretStr("production-access")
        kwargs["minio_secret_key"] = SecretStr("m" * 48)
    elif role == "analysis-worker":
        kwargs["analysis_rabbitmq_url"] = "amqp://app:mq-secret@rabbitmq:5672/"
        kwargs["analysis_minio_access_key"] = SecretStr("production-access")
        kwargs["analysis_minio_secret_key"] = SecretStr("m" * 48)
    elif role == "report-worker":
        kwargs["minio_access_key"] = SecretStr("production-access")
        kwargs["minio_secret_key"] = SecretStr("m" * 48)
    elif role == "provider-canary":
        kwargs["rabbitmq_url"] = "amqp://app:mq-secret@rabbitmq:5672/"
        kwargs["runner_hmac_secret"] = SecretStr("r" * 48)
        kwargs["minio_access_key"] = SecretStr("production-access")
        kwargs["minio_secret_key"] = SecretStr("m" * 48)

    # All roles share the same default URL key; leaving it unset must fail closed.
    with pytest.raises(ValidationError, match="production secrets"):
        Settings(**kwargs, url_encryption_key=SecretStr(DEFAULT_URL_ENCRYPTION_KEY))


def test_analysis_cli_settings_use_host_services_without_api_keys() -> None:
    settings = Settings(app_env="test", _env_file=None)

    assert settings.analysis_cli_provider == "codex"
    assert "analysis_schema_version" not in type(settings).model_fields
    assert "analysis_prompt_version" not in type(settings).model_fields
    assert "localhost:15432" in settings.analysis_database_url
    assert not any("openai" in name for name in type(settings).model_fields)


def test_analysis_worker_uses_compose_role_credentials_when_not_overridden() -> None:
    access = SecretStr("analysis-role-access")
    secret = SecretStr("analysis-role-secret")
    settings = Settings(
        app_env="test",
        service_role="analysis-worker",
        minio_access_key=SecretStr("shared-access"),
        minio_secret_key=SecretStr("shared-secret"),
        minio_analysis_access_key=access,
        minio_analysis_secret_key=secret,
        _env_file=None,
    )

    assert settings.analysis_minio_credentials() == (access, secret)


def test_analysis_worker_prefers_dedicated_minio_credentials() -> None:
    access = SecretStr("analysis-access")
    secret = SecretStr("analysis-secret")
    settings = Settings(
        app_env="test",
        service_role="analysis-worker",
        minio_access_key=SecretStr("shared-access"),
        minio_secret_key=SecretStr("shared-secret"),
        analysis_minio_access_key=access,
        analysis_minio_secret_key=secret,
        _env_file=None,
    )

    assert settings.analysis_minio_credentials() == (access, secret)


def test_analysis_worker_rejects_partial_minio_override() -> None:
    with pytest.raises(ValidationError, match="must be configured together"):
        Settings(
            app_env="test",
            service_role="analysis-worker",
            analysis_minio_access_key=SecretStr("analysis-access"),
            _env_file=None,
        )
