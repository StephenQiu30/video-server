from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunnerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore",
        case_sensitive=False,
    )

    runner_hmac_secret: SecretStr
    runner_egress_proxy: str
    runner_workspace_root: Path = Path("/var/lib/video-runner")

    runner_ytdlp_bin: str = "yt-dlp"
    runner_ytdlp_js_runtime: str = "node"
    runner_ffmpeg_bin: str = "ffmpeg"
    runner_ffprobe_bin: str = "ffprobe"

    runner_signature_max_age_seconds: int = Field(default=30, ge=1, le=300)
    runner_signature_future_skew_seconds: int = Field(default=5, ge=0, le=60)
    runner_nonce_ttl_seconds: int = Field(default=60, ge=2, le=600)
    runner_nonce_max_entries: int = Field(default=100_000, ge=100, le=1_000_000)
    runner_max_request_bytes: int = Field(default=64 * 1024, ge=1024, le=1024**2)

    runner_inspect_timeout_seconds: float = Field(default=30, gt=0, le=120)
    runner_download_timeout_seconds: float = Field(default=1800, gt=0, le=7200)
    runner_terminate_grace_seconds: float = Field(default=3, gt=0, le=30)
    runner_output_capture_bytes: int = Field(default=1024**2, ge=4096, le=8 * 1024**2)

    runner_max_duration_seconds: float = Field(default=7200, gt=0, le=86_400)
    runner_max_output_files: int = Field(default=3, ge=1, le=10)
    runner_max_output_bytes: int = Field(default=2 * 1024**3, ge=1024)
    runner_max_workspace_bytes: int = Field(default=4 * 1024**3, ge=1024)
    runner_max_candidate_streams: int = Field(default=200, ge=1, le=1000)
    runner_max_options: int = Field(default=50, ge=1, le=200)
    runner_max_thumbnail_bytes: int = Field(
        default=1_500_000,
        ge=16 * 1024,
        le=1_500_000,
    )
    runner_max_probe_sample_bytes: int = Field(
        default=8 * 1024**2,
        ge=1024**2,
        le=64 * 1024**2,
    )
    runner_max_active_tasks: int = Field(default=32, ge=1, le=256)
    runner_workspace_poll_interval_seconds: float = Field(
        default=0.25,
        ge=0.01,
        le=5,
    )
    runner_duration_tolerance_seconds: float = Field(default=3, ge=0, le=30)

    @field_validator("runner_hmac_secret")
    @classmethod
    def validate_hmac_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("runner HMAC secret must contain at least 32 bytes")
        return value

    @field_validator("runner_egress_proxy")
    @classmethod
    def validate_proxy(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("runner egress proxy is invalid") from exc
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise ValueError("runner egress proxy must be HTTP(S)")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("runner egress proxy cannot contain credentials")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("runner egress proxy must contain authority only")
        return value.rstrip("/")

    @field_validator("runner_workspace_root")
    @classmethod
    def resolve_workspace(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator(
        "runner_ytdlp_bin",
        "runner_ytdlp_js_runtime",
        "runner_ffmpeg_bin",
        "runner_ffprobe_bin",
    )
    @classmethod
    def validate_binary(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("runner binary name is invalid")
        return value

    @property
    def hmac_secret_bytes(self) -> bytes:
        return self.runner_hmac_secret.get_secret_value().encode()
