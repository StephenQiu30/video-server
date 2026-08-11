"""Typed configuration shared by API, workers and media runner."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.runner.provider_instances import validated_instance_hosts

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
    service_role: Literal[
        "api",
        "outbox",
        "download-worker",
        "analysis-worker",
        "report-worker",
        "provider-canary",
    ] = "api"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8101, ge=1, le=65535)
    app_version: str = "0.1.0"
    frontend_dist_dir: Path = REPOSITORY_ROOT / "frontend" / "out"
    readiness_timeout_seconds: float = Field(default=2.0, ge=0.1, le=10)
    request_max_bytes: int = Field(default=256 * 1024, ge=1024, le=4 * 1024 * 1024)
    request_timeout_seconds: float = Field(default=30, ge=1, le=300)
    metrics_access_key: SecretStr = SecretStr(
        "development-metrics-access-key-change-me"
    )

    database_url: str = "postgresql+asyncpg://video:video@localhost:15432/video"
    rabbitmq_url: str = "amqp://video-api:video-api-secret@localhost:5673/video"
    rabbitmq_vhost: str = Field(
        default="video",
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    rabbitmq_exchange: str = "video.events"
    download_queue: str = "video.download"
    download_routing_key: Literal["download.requested"] = "download.requested"
    analysis_queue: str = "video.analysis"
    analysis_routing_key: Literal["analysis.requested"] = "analysis.requested"
    analysis_report_queue: str = "video.analysis-report"
    analysis_report_routing_key: Literal["analysis.report.publish.requested"] = (
        "analysis.report.publish.requested"
    )
    rabbitmq_connection_timeout_seconds: float = Field(default=10, ge=1, le=60)
    rabbitmq_publish_timeout_seconds: float = Field(default=10, ge=1, le=60)
    rabbitmq_heartbeat_seconds: int = Field(default=60, ge=10, le=600)
    rabbitmq_reconnect_interval_seconds: float = Field(default=5, ge=1, le=60)
    worker_prefetch: int = Field(default=2, ge=1, le=32)
    download_worker_threads: int = Field(default=4, ge=1, le=64)
    outbox_batch_size: int = Field(default=50, ge=1, le=200)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)
    valkey_url: str | None = None

    minio_endpoint: str = "localhost:19190"
    minio_public_endpoint: str = "127.0.0.1:19190"
    minio_access_key: SecretStr = SecretStr("video-api-access")
    minio_secret_key: SecretStr = SecretStr("video-api-secret-change-me")
    minio_internal_secure: bool = False
    minio_public_secure: bool = False
    minio_region: str = "us-east-1"
    minio_bucket: str = "video-artifacts"

    auth_jwt_secret: SecretStr = SecretStr("development-jwt-secret-change-me-32-bytes")
    auth_jwt_issuer: str = Field(default="video-server", min_length=1, max_length=128)
    auth_jwt_audience: str = Field(default="video-web", min_length=1, max_length=128)
    auth_access_cookie_name: str = Field(
        default="video_access_token", min_length=1, max_length=128
    )
    auth_refresh_cookie_name: str = Field(
        default="video_refresh_token", min_length=1, max_length=128
    )
    auth_access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    auth_refresh_token_ttl_seconds: int = Field(
        default=2_592_000, ge=3600, le=31_536_000
    )
    auth_bootstrap_admin_email: EmailStr | None = None
    request_fingerprint_secret: SecretStr = SecretStr(
        "development-fingerprint-secret-change-me"
    )
    url_encryption_key: SecretStr = SecretStr(DEFAULT_URL_ENCRYPTION_KEY)
    url_encryption_key_id: str = Field(
        default="fernet-v1",
        min_length=1,
        max_length=32,
        pattern=r"^[a-z0-9_-]+$",
    )

    runner_base_url: str = "http://localhost:19100"
    runner_operator_base_urls: dict[str, str] = Field(default_factory=dict)
    runner_workspace_root: Path = Path("/work")
    runner_hmac_secret: SecretStr = SecretStr("development-runner-secret-change-me")
    provider_canary_targets: SecretStr = SecretStr("[]")
    provider_verified_keys: frozenset[str] = frozenset()
    peertube_allowed_instances: frozenset[str] = frozenset()
    provider_canary_metadata_interval_seconds: int = Field(
        default=21_600, ge=300, le=604_800
    )
    provider_canary_media_interval_seconds: int = Field(
        default=86_400, ge=300, le=2_592_000
    )
    provider_canary_poll_seconds: float = Field(default=60, ge=5, le=3600)
    runner_signature_ttl_seconds: int = Field(default=30, ge=5, le=300)
    inspect_timeout_seconds: int = Field(default=30, ge=1, le=300)
    download_timeout_seconds: int = Field(default=1800, ge=1, le=7200)
    max_video_duration_seconds: int = Field(default=7200, ge=1, le=86400)
    max_file_size_bytes: int = Field(default=2 * 1024**3, ge=1, le=20 * 1024**3)
    max_workspace_size_bytes: int = Field(default=4 * 1024**3, ge=1, le=40 * 1024**3)
    inspection_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    artifact_ttl_seconds: int = Field(default=86400, ge=300, le=2592000)
    artifact_gc_interval_seconds: float = Field(default=300, ge=5, le=86400)
    artifact_gc_batch_size: int = Field(default=50, ge=1, le=200)
    artifact_delete_timeout_seconds: float = Field(default=30, ge=1, le=300)
    artifact_download_url_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    job_lease_seconds: int = Field(default=60, ge=15, le=600)
    heartbeat_interval_seconds: int = Field(default=15, ge=5, le=120)
    max_download_attempts: int = Field(default=3, ge=1, le=10)
    max_analysis_attempts: int = Field(default=3, ge=1, le=10)
    download_queued_recovery_seconds: int = Field(default=60, ge=15, le=3600)
    analysis_max_runs_per_job: int = Field(default=10, ge=1, le=100)
    analysis_queued_recovery_seconds: int = Field(default=60, ge=15, le=3600)
    analysis_worker_heartbeat_seconds: float = Field(default=10, ge=1, le=60)
    analysis_worker_stale_seconds: int = Field(default=45, ge=5, le=300)
    analysis_manual_retry_min_interval_seconds: int = Field(default=30, ge=0, le=86400)
    analysis_manual_retries_per_day: int = Field(default=20, ge=1, le=1000)
    analysis_report_ttl_seconds: int = Field(default=86400, ge=300, le=2592000)
    analysis_report_gc_interval_seconds: float = Field(default=300, ge=5, le=86400)
    analysis_report_gc_batch_size: int = Field(default=50, ge=1, le=200)
    analysis_report_orphan_grace_seconds: int = Field(default=3600, ge=300, le=604800)
    websocket_max_connections: int = Field(default=1000, ge=1, le=100000)
    websocket_max_connections_per_owner: int = Field(default=4, ge=1, le=100)
    websocket_auth_recheck_seconds: float = Field(default=15, ge=1, le=300)

    analysis_enabled: bool = True
    analysis_workspace_root: Path = Path("./.analysis-work")
    analysis_cli_provider: Literal["codex", "claude"] = "codex"
    analysis_codex_binary: Path = Path("codex")
    analysis_codex_model: str = Field(default="gpt-5.6-sol", min_length=1)
    analysis_claude_binary: Path = Path("claude")
    analysis_claude_model: str = Field(default="sonnet", min_length=1)
    analysis_ffmpeg_binary: Path = Path("ffmpeg")
    analysis_ffprobe_binary: Path = Path("ffprobe")
    analysis_timeout_seconds: float = Field(default=900, ge=1, le=3600)
    analysis_max_stdout_bytes: int = Field(default=2 * 1024**2, ge=1024)
    analysis_max_stderr_bytes: int = Field(default=128 * 1024, ge=1024)
    analysis_max_workspace_bytes: int = Field(default=4 * 1024**3, ge=1024)
    analysis_max_workspace_files: int = Field(default=512, ge=8, le=4096)
    analysis_max_frames: int = Field(default=256, ge=1, le=1024)
    analysis_max_image_bytes: int = Field(default=20 * 1024**2, ge=1024)
    analysis_workspace_poll_seconds: float = Field(default=0.25, ge=0.05, le=5)
    analysis_terminate_grace_seconds: float = Field(default=2, ge=0.1, le=30)
    analysis_claude_max_turns: int = Field(default=40, ge=1, le=100)
    analysis_database_url: str = (
        "postgresql+asyncpg://video:video@localhost:15432/video"
    )
    analysis_rabbitmq_url: str = (
        "amqp://video-analysis:video-analysis-secret@localhost:5673/video"
    )
    analysis_minio_endpoint: str = "localhost:19190"
    analysis_minio_access_key: SecretStr = SecretStr("video-analysis-access")
    analysis_minio_secret_key: SecretStr = SecretStr("video-analysis-secret-change-me")

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

    @field_validator("auth_bootstrap_admin_email", mode="before")
    @classmethod
    def empty_bootstrap_admin_email_to_none(cls, value: object) -> object | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("runner_operator_base_urls")
    @classmethod
    def validate_runner_operator_urls(cls, value: dict[str, str]) -> dict[str, str]:
        validated: dict[str, str] = {}
        for provider, endpoint in value.items():
            if re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", provider) is None:
                raise ValueError("runner operator provider key is invalid")
            try:
                parsed = urlsplit(endpoint)
                _ = parsed.port
            except ValueError as exc:
                raise ValueError("runner operator URL is invalid") from exc
            if (
                parsed.scheme != "http"
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("runner operator URL must be an internal HTTP URL")
            validated[provider] = endpoint.rstrip("/")
        return validated

    @field_validator("url_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode())
        except (TypeError, ValueError) as exc:
            raise ValueError("URL_ENCRYPTION_KEY must be a Fernet key") from exc
        return value

    @field_validator("provider_verified_keys")
    @classmethod
    def validate_provider_verified_keys(cls, value: frozenset[str]) -> frozenset[str]:
        if any(re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", key) is None for key in value):
            raise ValueError("PROVIDER_VERIFIED_KEYS contains an invalid key")
        return value

    @field_validator("peertube_allowed_instances")
    @classmethod
    def validate_peertube_instances(cls, value: frozenset[str]) -> frozenset[str]:
        return validated_instance_hosts(value)

    @field_validator(
        "auth_jwt_secret",
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
        if self.analysis_worker_stale_seconds <= self.analysis_worker_heartbeat_seconds:
            raise ValueError(
                "analysis worker stale window must exceed its heartbeat interval"
            )
        if self.app_env != "production":
            return self
        secret_values: list[str] = []
        if self.service_role == "api":
            secret_values.extend(
                (
                    self.auth_jwt_secret.get_secret_value(),
                    self.request_fingerprint_secret.get_secret_value(),
                    self.runner_hmac_secret.get_secret_value(),
                    self.metrics_access_key.get_secret_value(),
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
                    self.analysis_minio_access_key.get_secret_value(),
                    self.analysis_minio_secret_key.get_secret_value(),
                )
            )
        elif self.service_role == "report-worker":
            secret_values.extend(
                (
                    self.minio_access_key.get_secret_value(),
                    self.minio_secret_key.get_secret_value(),
                )
            )
        elif self.service_role == "provider-canary":
            secret_values.extend(
                (
                    self.runner_hmac_secret.get_secret_value(),
                    self.minio_access_key.get_secret_value(),
                    self.minio_secret_key.get_secret_value(),
                )
            )
        insecure = any(
            value.startswith(("development-", "video-")) or "replace-with" in value
            for value in secret_values
        )
        rabbitmq_url = ""
        if self.service_role == "analysis-worker":
            rabbitmq_url = self.analysis_rabbitmq_url
        elif self.service_role != "provider-canary":
            rabbitmq_url = self.rabbitmq_url
        insecure_urls = any(
            marker in f"{self.database_url} {rabbitmq_url}"
            for marker in ("video:video@", "replace-with", "-secret@")
        )
        default_url_key = self.service_role in {
            "api",
            "download-worker",
            "provider-canary",
        } and (self.url_encryption_key.get_secret_value() == DEFAULT_URL_ENCRYPTION_KEY)
        if insecure or insecure_urls or default_url_key:
            raise ValueError("production secrets must be explicitly configured")
        if self.service_role == "api" and not self.valkey_url:
            raise ValueError("production API requires VALKEY_URL")
        if self.service_role == "api" and self.auth_bootstrap_admin_email is None:
            raise ValueError("production API requires AUTH_BOOTSTRAP_ADMIN_EMAIL")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_settings_for_role(
    role: Literal[
        "api",
        "outbox",
        "download-worker",
        "analysis-worker",
        "report-worker",
        "provider-canary",
    ],
) -> Settings:
    return Settings(service_role=role)
