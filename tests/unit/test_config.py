from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.core.config import Settings, get_settings

REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://video:video@localhost:5432/video",
    "RABBITMQ_URL": "amqp://video:video@localhost:5672/",
    "MINIO_ENDPOINT": "localhost:9000",
    "MINIO_ACCESS_KEY": "video-access",
    "MINIO_SECRET_KEY": "video-secret",
    "MINIO_BUCKET": "video-artifacts",
    "SESSION_SECRET": "a-development-session-secret-with-sufficient-length",
}


@pytest.fixture
def configured_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_settings_loads_required_values_and_environment_overrides(
    configured_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_PORT", "19090")
    monkeypatch.setenv("WORKER_CONCURRENCY", "3")

    settings = Settings()

    assert settings.database_url == REQUIRED_ENV["DATABASE_URL"]
    assert settings.app_port == 19090
    assert settings.worker_concurrency == 3
    assert settings.minio_secure is False


def test_settings_rejects_missing_required_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", REQUIRED_ENV["DATABASE_URL"])
    monkeypatch.setenv("RABBITMQ_URL", REQUIRED_ENV["RABBITMQ_URL"])
    monkeypatch.setenv("MINIO_ENDPOINT", REQUIRED_ENV["MINIO_ENDPOINT"])
    monkeypatch.setenv("MINIO_ACCESS_KEY", REQUIRED_ENV["MINIO_ACCESS_KEY"])
    monkeypatch.setenv("MINIO_BUCKET", REQUIRED_ENV["MINIO_BUCKET"])
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_rejects_invalid_port_and_bounds(configured_env: None) -> None:
    with pytest.raises(ValidationError):
        Settings(app_port=0)

    with pytest.raises(ValidationError):
        Settings(worker_concurrency=0)


def test_settings_parses_comma_separated_extractors(configured_env: None) -> None:
    settings = Settings(ytdlp_allowed_extractors="youtube,tiktok")  # type: ignore[arg-type]

    assert settings.ytdlp_allowed_extractors == ("youtube", "tiktok")


def test_get_settings_is_cached(configured_env: None) -> None:
    first = get_settings()
    second = get_settings()

    assert first is second
