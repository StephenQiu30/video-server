"""Typed configuration shared by API, workers and media runner."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_URL_ENCRYPTION_KEY = "ZGV2ZWxvcG1lbnQtdXJsLWtleS0zMi1ieXRlcyEhISE="


class Settings(BaseSettings):
    """Load one validated configuration model from the root environment."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    service_role: Literal["api", "outbox", "download-worker", "analysis-worker"] = "api"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8101, ge=1, le=65535)
    app_version: str = "0.1.0"
    frontend_dist_dir: Path = REPOSITORY_ROOT / "frontend" / "dist"
    readiness_timeout_seconds: float = Field(default=2.0, ge=0.1, le=10)

    database_url: str = "postgresql+asyncpg://video:video@localhost:15432/video"
    rabbitmq_url: str = "amqp://video:video@localhost:5673/"
    rabbitmq_exchange: str = "video.events"
    download_queue: str = "video.download"
    download_routing_key: Literal["download.requested"] = "download.requested"
    analysis_queue: str = "video.analysis"
    analysis_routing_key: Literal["analysis.requested"] = "analysis.requested"
    worker_prefetch: int = Field(default=2, ge=1, le=32)
    outbox_batch_size: int = Field(default=50, ge=1, le=200)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)

    minio_endpoint: str = "localhost:19190"
    minio_public_endpoint: str = "localhost:19190"
    minio_access_key: SecretStr = SecretStr("video-app-access")
    minio_secret_key: SecretStr = SecretStr("video-app-secret-change-me")
    minio_internal_secure: bool = False
    minio_public_secure: bool = False
    minio_region: str = "us-east-1"
    minio_bucket: str = "video-artifacts"

    session_secret: SecretStr = SecretStr("development-session-secret-change-me")
    request_fingerprint_secret: SecretStr = SecretStr(
        "development-fingerprint-secret-change-me"
    )
    session_cookie_name: str = "video_session"
    session_ttl_seconds: int = Field(default=86400, ge=300, le=2592000)
    url_encryption_key: SecretStr = SecretStr(DEFAULT_URL_ENCRYPTION_KEY)
    url_encryption_key_id: str = Field(
        default="fernet-v1",
        min_length=1,
        max_length=32,
        pattern=r"^[a-z0-9_-]+$",
    )

    runner_base_url: str = "http://localhost:19100"
    runner_workspace_root: Path = Path("/work")
    runner_hmac_secret: SecretStr = SecretStr("development-runner-secret-change-me")
    runner_signature_ttl_seconds: int = Field(default=30, ge=5, le=300)
    inspect_timeout_seconds: int = Field(default=30, ge=1, le=300)
    download_timeout_seconds: int = Field(default=1800, ge=1, le=7200)
    max_video_duration_seconds: int = Field(default=7200, ge=1, le=86400)
    max_file_size_bytes: int = Field(default=2 * 1024**3, ge=1, le=20 * 1024**3)
    max_workspace_size_bytes: int = Field(default=4 * 1024**3, ge=1, le=40 * 1024**3)
    inspection_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    artifact_ttl_seconds: int = Field(default=86400, ge=300, le=2592000)
    artifact_download_url_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    job_lease_seconds: int = Field(default=60, ge=15, le=600)
    heartbeat_interval_seconds: int = Field(default=15, ge=5, le=120)
    max_download_attempts: int = Field(default=3, ge=1, le=10)
    max_analysis_attempts: int = Field(default=3, ge=1, le=10)

    analysis_workspace_root: Path = Path("/analysis-work")
    analysis_provider: Literal["deepseek", "ollama"] = "ollama"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_analysis_model: str = "deepseek-v4-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_analysis_model: str = "deepseek-r1:8b"
    analysis_max_output_tokens: int = Field(default=16_384, ge=1_024, le=131_072)
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    analysis_schema_version: str = "analysis.v1"
    analysis_timeout_seconds: float = Field(default=120, ge=1, le=1800)
    transcription_timeout_seconds: float = Field(default=300, ge=1, le=1800)

    @field_validator("frontend_dist_dir")
    @classmethod
    def resolve_frontend_dist(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = REPOSITORY_ROOT / value
        return value.resolve()

    @field_validator("runner_workspace_root")
    @classmethod
    def resolve_workspace(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("analysis_workspace_root")
    @classmethod
    def absolute_analysis_workspace(cls, value: Path) -> Path:
        return value.expanduser().absolute()

    @field_validator("url_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode())
        except (TypeError, ValueError) as exc:
            raise ValueError("URL_ENCRYPTION_KEY must be a Fernet key") from exc
        return value

    @field_validator(
        "session_secret",
        "request_fingerprint_secret",
        "runner_hmac_secret",
    )
    @classmethod
    def validate_signing_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("signing secrets must contain at least 32 bytes")
        return value

    @model_validator(mode="after")
    def reject_development_secrets_in_production(self) -> Settings:
        if self.app_env != "production":
            return self
        secret_values: list[str] = []
        if self.service_role == "api":
            secret_values.extend(
                (
                    self.session_secret.get_secret_value(),
                    self.request_fingerprint_secret.get_secret_value(),
                    self.runner_hmac_secret.get_secret_value(),
                    self.minio_access_key.get_secret_value(),
                    self.minio_secret_key.get_secret_value(),
                )
            )
        elif self.service_role == "download-worker":
            secret_values.extend(
                (
                    self.runner_hmac_secret.get_secret_value(),
                    self.minio_access_key.get_secret_value(),
                    self.minio_secret_key.get_secret_value(),
                )
            )
        elif self.service_role == "analysis-worker":
            secret_values.extend(
                (
                    self.minio_access_key.get_secret_value(),
                    self.minio_secret_key.get_secret_value(),
                )
            )
        if self.service_role == "analysis-worker" and self.openai_api_key is not None:
            secret_values.append(self.openai_api_key.get_secret_value())
        if self.service_role == "analysis-worker" and self.deepseek_api_key is not None:
            secret_values.append(self.deepseek_api_key.get_secret_value())
        insecure = any(
            value.startswith(("development-", "video-")) or "replace-with" in value
            for value in secret_values
        )
        insecure_urls = "video:video@" in self.database_url or "video:video@" in (
            self.rabbitmq_url
        )
        default_url_key = self.service_role in {"api", "download-worker"} and (
            self.url_encryption_key.get_secret_value() == DEFAULT_URL_ENCRYPTION_KEY
        )
        if insecure or insecure_urls or default_url_key:
            raise ValueError("production secrets must be explicitly configured")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
