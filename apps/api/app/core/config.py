from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_name: str = "Stephen Video Downloader"
    app_env: str = "local"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    database_url: str = "postgresql+psycopg://video:video@127.0.0.1:5432/video_downloader"
    redis_url: str = "redis://127.0.0.1:6379/0"
    rq_queue_name: str = "downloads"

    jwt_secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    registration_enabled: bool = True
    registration_invite_code: str | None = None
    admin_emails: str = ""
    default_daily_task_quota: int = 10
    default_storage_quota_bytes: int = 5 * 1024 * 1024 * 1024

    download_work_dir: str = Field(
        default="./tmp/download-workdir",
        validation_alias=AliasChoices("DOWNLOAD_WORK_DIR", "DOWNLOAD_DIR"),
    )
    max_file_size_bytes: int = 2 * 1024 * 1024 * 1024
    max_task_runtime_seconds: int = 2 * 60 * 60
    global_download_concurrency: int = 2
    per_user_download_concurrency: int = 1
    file_retention_hours: int = 24
    presigned_url_ttl_seconds: int = 15 * 60
    ytdlp_cookies_from_browser: str | None = None

    s3_endpoint_url: str = "http://127.0.0.1:9000"
    s3_public_endpoint_url: str | None = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket: str = "video-downloads"
    s3_region: str = "us-east-1"
    s3_force_path_style: bool = True

    # AI Intelligence Suite
    llm_api_key: str | None = None
    llm_api_base_url: str = "https://api.deepseek.com/v1"
    llm_model_name: str = "deepseek-chat"
    transcription_api_key: str | None = None
    transcription_api_base_url: str = "https://api.groq.com/openai/v1"
    transcription_model_name: str = "whisper-large-v3"
    
    # GitHub OAuth
    github_client_id: str | None = None
    github_client_secret: str | None = None

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def admin_email_set(self) -> set[str]:
        return {email.strip().lower() for email in self.admin_emails.split(",") if email.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
