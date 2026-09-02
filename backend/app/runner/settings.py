from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.providers import (
    ProviderAccessMode,
    ProviderKey,
    ProviderSessionVersion,
)
from app.runner.provider_instances import validated_instance_hosts
from app.runner.version import (
    YOUTUBE_POT_PROVIDER_ATTESTATION,
    YTDLP_ENGINE_COMMIT,
)

_PROVIDER_KEY = re.compile(r"[a-z][a-z0-9_-]{0,31}")
_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class RunnerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore",
        case_sensitive=False,
    )

    runner_hmac_secret: SecretStr
    runner_egress_proxy: str
    runner_provider_egress_proxies: dict[str, str] = Field(default_factory=dict)
    runner_workspace_root: Path = Path("/var/lib/video-runner")
    runner_access_mode: ProviderAccessMode = ProviderAccessMode.ANONYMOUS
    runner_operator_session_versions: dict[ProviderKey, ProviderSessionVersion] = Field(
        default_factory=dict
    )
    runner_operator_account_baseline_attested: bool = False
    runner_provider_session_temp_root: Path = Path("/run/provider-session")
    runner_provider_cookie_sync_root: Path | None = None
    peertube_allowed_instances: frozenset[str] = frozenset()

    runner_ytdlp_bin: str = "yt-dlp"
    runner_ytdlp_js_runtime: str = "node"
    runner_ytdlp_commit: str = YTDLP_ENGINE_COMMIT
    runner_youtube_pot_base_url: str | None = None
    runner_youtube_pot_provider_version: str = YOUTUBE_POT_PROVIDER_ATTESTATION
    runner_ffmpeg_bin: str = "ffmpeg"
    runner_ffprobe_bin: str = "ffprobe"

    runner_signature_max_age_seconds: int = Field(default=30, ge=1, le=300)
    runner_signature_future_skew_seconds: int = Field(default=5, ge=0, le=60)
    runner_nonce_ttl_seconds: int = Field(default=60, ge=2, le=600)
    runner_nonce_max_entries: int = Field(default=100_000, ge=100, le=1_000_000)
    runner_max_request_bytes: int = Field(default=64 * 1024, ge=1024, le=1024**2)

    runner_inspect_timeout_seconds: float = Field(default=120, gt=0, le=120)
    runner_download_timeout_seconds: float = Field(default=7200, gt=0, le=7200)
    runner_terminate_grace_seconds: float = Field(default=3, gt=0, le=30)
    runner_output_capture_bytes: int = Field(default=1024**2, ge=4096, le=8 * 1024**2)

    runner_max_duration_seconds: float = Field(default=86_400, gt=0, le=86_400)
    runner_max_output_files: int = Field(default=3, ge=1, le=10)
    runner_max_output_bytes: int = Field(default=20 * 1024**3, ge=1024)
    runner_max_workspace_bytes: int = Field(default=40 * 1024**3, ge=1024)
    runner_max_gallery_assets: int = Field(default=100, ge=1, le=1000)
    runner_max_gallery_asset_bytes: int = Field(
        default=25 * 1024**2, ge=64 * 1024, le=512 * 1024**2
    )
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

    @field_validator("peertube_allowed_instances")
    @classmethod
    def validate_peertube_instances(cls, value: frozenset[str]) -> frozenset[str]:
        return validated_instance_hosts(value)

    @field_validator("runner_egress_proxy")
    @classmethod
    def validate_proxy(cls, value: str) -> str:
        return _validate_proxy(value)

    @field_validator("runner_provider_egress_proxies")
    @classmethod
    def validate_provider_proxies(cls, value: dict[str, str]) -> dict[str, str]:
        validated: dict[str, str] = {}
        for provider, proxy in value.items():
            if _PROVIDER_KEY.fullmatch(provider) is None:
                raise ValueError("provider proxy key is invalid")
            validated[provider] = _validate_proxy(proxy)
        return validated

    def egress_proxy_for(self, provider: str) -> str:
        return self.runner_provider_egress_proxies.get(
            provider,
            self.runner_egress_proxy,
        )

    def egress_affinity_for(self, provider: str) -> str:
        if provider in self.runner_provider_egress_proxies:
            return egress_affinity_id(
                f"provider:{provider}",
                self.runner_provider_egress_proxies[provider],
            )
        return egress_affinity_id("default", self.runner_egress_proxy)

    @field_validator(
        "runner_workspace_root",
        "runner_provider_session_temp_root",
    )
    @classmethod
    def resolve_workspace(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("runner_provider_cookie_sync_root")
    @classmethod
    def normalize_cookie_sync_root(cls, value: Path | None) -> Path | None:
        if value is None:
            return None
        return value.expanduser().resolve()

    @field_validator("runner_ytdlp_commit", "runner_youtube_pot_provider_version")
    @classmethod
    def validate_version_reference(cls, value: str) -> str:
        if _REFERENCE.fullmatch(value) is None:
            raise ValueError("runner version reference is invalid")
        return value

    @field_validator("runner_youtube_pot_base_url")
    @classmethod
    def validate_pot_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return _validate_service_url(value)

    @model_validator(mode="after")
    def validate_session_boundary(self) -> RunnerSettings:
        if self.runner_provider_session_temp_root.is_relative_to(
            self.runner_workspace_root
        ):
            raise ValueError("provider session temp root cannot be in the workspace")
        operator = self.runner_access_mode is ProviderAccessMode.OPERATOR_MANAGED
        if self.runner_provider_cookie_sync_root is not None:
            if not operator:
                raise ValueError(
                    "provider Cookie sync is restricted to an operator runner"
                )
            if self.runner_provider_cookie_sync_root.is_relative_to(
                self.runner_workspace_root
            ):
                raise ValueError("cookie sync root cannot be in the workspace")
        if operator:
            providers = set(self.runner_operator_session_versions)
            if len(providers) != 1:
                raise ValueError(
                    "operator runner requires exactly one provider session"
                )
            provider = next(iter(providers))
            from app.runner.provider_registry import default_provider_registry
            from app.runner.provider_session_policy import browser_session_policy

            profile = next(
                (
                    item
                    for item in default_provider_registry().profiles
                    if item.key == provider
                ),
                None,
            )
            if (
                profile is None
                or ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes
            ):
                raise ValueError("operator provider is not allowlisted")
            try:
                policy = browser_session_policy(provider)
            except Exception as exc:
                raise ValueError("operator provider is not allowlisted") from exc
            if self.runner_operator_session_versions[provider] is not policy.version:
                raise ValueError("operator session version does not match policy")
            if not self.runner_operator_account_baseline_attested:
                raise ValueError("operator account baseline must be attested")
            if self.runner_max_active_tasks != 1:
                raise ValueError("operator runner concurrency must be one")
            if self.runner_provider_cookie_sync_root is None:
                raise ValueError("operator runner requires provider Cookie sync")
        elif self.runner_operator_session_versions:
            raise ValueError("anonymous runner cannot configure provider sessions")
        if self.runner_youtube_pot_base_url is not None:
            youtube_operator = operator and set(
                self.runner_operator_session_versions
            ) == {ProviderKey.YOUTUBE}
            if (
                not youtube_operator
                and self.runner_access_mode is not ProviderAccessMode.ANONYMOUS
            ):
                raise ValueError("POT provider is restricted to the YouTube operator")
        return self

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


def get_runner_settings() -> RunnerSettings:
    """Load the same root environment used by local API and worker processes."""
    return RunnerSettings(
        _env_file=REPOSITORY_ROOT / ".env",
        _env_file_encoding="utf-8",
    )


def _validate_proxy(value: str) -> str:
    if value != value.strip():
        raise ValueError("runner egress proxy is invalid")
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


def _validate_service_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("provider service URL is invalid") from exc
    if parsed.scheme != "http" or parsed.hostname is None:
        raise ValueError("provider service URL must use HTTP")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("provider service URL cannot contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("provider service URL cannot contain query or fragment")
    return value.rstrip("/")


def egress_affinity_id(scope: str, proxy_url: str) -> str:
    """Return a non-secret identity that changes whenever an egress route changes."""
    fingerprint = sha256(proxy_url.encode()).hexdigest()[:12]
    return f"{scope}:{fingerprint}"
