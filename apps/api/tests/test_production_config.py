import pytest

from app.core.production import validate_production_settings


class DummySettings:
    app_env = "production"
    jwt_secret_key = "change-me-in-production"
    registration_enabled = True
    registration_invite_code = None
    s3_access_key_id = "minioadmin"
    s3_secret_access_key = "minioadmin"
    database_url = "postgresql+psycopg://video:safe-db-password@postgres:5432/video_downloader"
    redis_url = "redis://:safe-redis-password@redis:6379/0"


def test_validate_production_settings_rejects_default_jwt_secret() -> None:
    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(DummySettings())

    assert "JWT_SECRET_KEY" in str(exc_info.value)


def test_validate_production_settings_ignores_local_env() -> None:
    settings = DummySettings()
    settings.app_env = "local"

    validate_production_settings(settings)


def test_validate_production_settings_rejects_open_registration_without_invite() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "REGISTRATION_INVITE_CODE" in str(exc_info.value)


def test_validate_production_settings_rejects_default_storage_credentials() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"
    settings.registration_enabled = False

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "S3_ACCESS_KEY_ID" in str(exc_info.value)
    assert "S3_SECRET_ACCESS_KEY" in str(exc_info.value)


def test_validate_production_settings_rejects_default_database_password_only_from_url_password() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"
    settings.registration_enabled = False
    settings.s3_access_key_id = "safe-minio-user"
    settings.s3_secret_access_key = "safe-minio-secret"
    settings.database_url = "postgresql+psycopg://video:video@postgres:5432/video_downloader"

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "DATABASE_URL" in str(exc_info.value)


def test_validate_production_settings_allows_video_database_name_with_safe_password() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"
    settings.registration_enabled = False
    settings.s3_access_key_id = "safe-minio-user"
    settings.s3_secret_access_key = "safe-minio-secret"
    settings.database_url = "postgresql+psycopg://video:safe-db-password@postgres:5432/video_downloader"
    settings.redis_url = "redis://:safe-redis-password@redis:6379/0"

    validate_production_settings(settings)


def test_validate_production_settings_rejects_short_jwt_secret() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "too-short"

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "JWT_SECRET_KEY" in str(exc_info.value)


def test_validate_production_settings_rejects_localhost_database_url() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"
    settings.registration_enabled = False
    settings.database_url = "postgresql+psycopg://video:safe-db-password@localhost:5432/video_downloader"

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "DATABASE_URL" in str(exc_info.value)
    assert "localhost" in str(exc_info.value)


def test_validate_production_settings_rejects_localhost_redis_url() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"
    settings.registration_enabled = False
    settings.database_url = "postgresql+psycopg://video:safe-db-password@postgres:5432/video_downloader"
    settings.redis_url = "redis://:safe-redis-password@localhost:6379/0"

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "REDIS_URL" in str(exc_info.value)
    assert "localhost" in str(exc_info.value)


def test_validate_production_settings_rejects_127_0_0_1_database_url() -> None:
    settings = DummySettings()
    settings.jwt_secret_key = "safe-production-secret-value-with-32-chars"
    settings.registration_enabled = False
    settings.database_url = "postgresql+psycopg://video:safe-db-password@127.0.0.1:5432/video_downloader"

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_settings(settings)

    assert "DATABASE_URL" in str(exc_info.value)


def test_production_template_has_change_me_placeholders() -> None:
    """The .env.production.example must contain CHANGE_ME placeholders so it
    cannot be accidentally used as a real production config."""
    from pathlib import Path

    template_path = Path(__file__).resolve().parents[3] / ".env.production.example"
    assert template_path.exists(), f"Production template not found: {template_path}"
    content = template_path.read_text(encoding="utf-8")

    assert "CHANGE_ME" in content, "Production template must contain CHANGE_ME placeholders"
    # Ensure the most dangerous defaults are NOT present as real values
    assert "minioadmin" not in content.lower(), "Production template must not contain 'minioadmin'"
    assert content.count("CHANGE_ME") >= 5, "Production template should have CHANGE_ME for all secrets"
