from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import Settings
from pydantic import SecretStr, ValidationError


def test_settings_resolve_frontend_dist_from_repository_root() -> None:
    settings = Settings(app_env="test")

    assert settings.frontend_dist_dir.name == "dist"
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


def test_download_limits_are_validated() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="test", max_file_size_bytes=0)

    with pytest.raises(ValidationError):
        Settings(app_env="test", download_timeout_seconds=0)


def test_signing_secrets_require_adequate_entropy_capacity() -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(app_env="test", session_secret=SecretStr("too-short"))


def test_production_rejects_development_secrets() -> None:
    with pytest.raises(ValidationError, match="production secrets"):
        Settings(app_env="production")


def test_production_accepts_explicit_secrets() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://app:db-secret@postgres:5432/video",
        rabbitmq_url="amqp://app:mq-secret@rabbitmq:5672/",
        session_secret=SecretStr("s" * 48),
        request_fingerprint_secret=SecretStr("f" * 48),
        url_encryption_key=SecretStr("MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="),
        runner_hmac_secret=SecretStr("r" * 48),
        minio_access_key=SecretStr("production-access"),
        minio_secret_key=SecretStr("m" * 48),
    )

    assert settings.app_env == "production"


def test_production_rejects_default_url_encryption_key() -> None:
    with pytest.raises(ValidationError, match="production secrets"):
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://app:db-secret@postgres:5432/video",
            rabbitmq_url="amqp://app:mq-secret@rabbitmq:5672/",
            session_secret=SecretStr("s" * 48),
            request_fingerprint_secret=SecretStr("f" * 48),
            runner_hmac_secret=SecretStr("r" * 48),
            minio_access_key=SecretStr("production-access"),
            minio_secret_key=SecretStr("m" * 48),
        )
