from typing import Any
from urllib.parse import urlparse


DEFAULT_JWT_SECRET = "change-me-in-production"
DEFAULT_MINIO_VALUES = {"minioadmin"}
DEFAULT_PASSWORD_VALUES = {"video", "password", "changeme", "change-me"}


def validate_production_settings(settings: Any) -> None:
    if getattr(settings, "app_env", "local") != "production":
        return

    failures: list[str] = []
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if jwt_secret == DEFAULT_JWT_SECRET or len(jwt_secret) < 32:
        failures.append("JWT_SECRET_KEY must be replaced and at least 32 characters")

    if getattr(settings, "registration_enabled", False) and not getattr(settings, "registration_invite_code", None):
        failures.append("REGISTRATION_INVITE_CODE is required when registration is enabled")

    if getattr(settings, "s3_access_key_id", "") in DEFAULT_MINIO_VALUES:
        failures.append("S3_ACCESS_KEY_ID must not use the MinIO default")
    if getattr(settings, "s3_secret_access_key", "") in DEFAULT_MINIO_VALUES:
        failures.append("S3_SECRET_ACCESS_KEY must not use the MinIO default")

    if _password_from_url(getattr(settings, "database_url", "")) in DEFAULT_PASSWORD_VALUES:
        failures.append("DATABASE_URL must not use a default password")
    if _password_from_url(getattr(settings, "redis_url", "")) in DEFAULT_PASSWORD_VALUES:
        failures.append("REDIS_URL must not use a default password")

    for field in ("database_url", "redis_url"):
        hostname = _hostname_from_url(getattr(settings, field, ""))
        if hostname in {"localhost", "127.0.0.1", "0.0.0.0"}:
            failures.append(f"{field.upper()} must not point to localhost in production")

    if failures:
        raise RuntimeError("Production settings are unsafe: " + "; ".join(failures))


def _normalize_db_url(value: str) -> str:
    if value.startswith("postgresql+psycopg://"):
        return "postgresql://" + value.split("://", 1)[1]
    return value


def _password_from_url(value: str) -> str:
    return (urlparse(_normalize_db_url(value)).password or "").lower()


def _hostname_from_url(value: str) -> str:
    return (urlparse(_normalize_db_url(value)).hostname or "").lower()
