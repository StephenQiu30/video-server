"""Single typed configuration source for API, worker and migrations."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from the process environment and optional ``.env``.

    Infrastructure credentials intentionally have no Python defaults.  This
    makes a misconfigured process fail during startup rather than silently
    connecting to an unintended service.
    """

    model_config = SettingsConfigDict(
        env_file=(Path.cwd() / ".env"),
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: Annotated[int, Field(ge=1, le=65535)] = 19090
    app_public_origin: str = "http://localhost:19090"
    web_origin: str = "http://localhost:8000"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_version: str = "0.1.0"

    database_url: str

    rabbitmq_url: str
    rabbitmq_exchange: str = "video.downloads"
    rabbitmq_queue: str = "video.download"
    rabbitmq_routing_key: str = "video.download"
    rabbitmq_prefetch_count: Annotated[int, Field(ge=1, le=1000)] = 2

    minio_endpoint: str
    minio_public_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_bucket: str
    minio_presigned_url_ttl_seconds: Annotated[int, Field(ge=1, le=86400)] = 900

    session_secret: Annotated[str, Field(min_length=32)]
    session_cookie_name: str = "video_session"
    session_ttl_seconds: Annotated[int, Field(ge=60, le=604800)] = 86400

    ytdlp_allowed_extractors: Annotated[tuple[str, ...], NoDecode] = ("default",)
    inspect_timeout_seconds: Annotated[int, Field(ge=1, le=300)] = 30
    inspect_ttl_seconds: Annotated[int, Field(ge=60, le=86400)] = 900
    download_timeout_seconds: Annotated[int, Field(ge=1, le=7200)] = 1800
    max_video_duration_seconds: Annotated[int, Field(ge=1, le=86400)] = 7200
    max_file_size_bytes: Annotated[int, Field(ge=1, le=20 * 1024**3)] = 2 * 1024**3
    artifact_ttl_seconds: Annotated[int, Field(ge=60, le=604800)] = 86400
    job_tombstone_ttl_seconds: Annotated[int, Field(ge=60, le=2592000)] = 604800
    worker_concurrency: Annotated[int, Field(ge=1, le=32)] = 2
    worker_temp_dir: Path = Path("/tmp/video-downloads")
    progress_update_interval_seconds: Annotated[int, Field(ge=1, le=300)] = 5
    housekeeping_interval_seconds: Annotated[int, Field(ge=10, le=86400)] = 300
    running_stale_after_seconds: Annotated[int, Field(ge=60, le=86400)] = 900

    @field_validator("database_url", "rabbitmq_url", "minio_endpoint", "minio_bucket")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("configuration value must not be empty")
        return value

    @field_validator("ytdlp_allowed_extractors", mode="before")
    @classmethod
    def parse_extractors(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            parts = tuple(item.strip() for item in value.split(",") if item.strip())
        elif isinstance(value, (list, tuple, set)):
            parts = tuple(str(item).strip() for item in value if str(item).strip())
        else:
            raise TypeError("YTDLP_ALLOWED_EXTRACTORS must be comma-separated")
        if not parts:
            raise ValueError("at least one extractor is required")
        return parts


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings instance."""

    return Settings()
