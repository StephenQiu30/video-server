from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.application.ai_providers import (
    AiProviderAuthMode,
    AiProviderEngine,
    AiProviderProfile,
    AiProviderRepository,
)
from app.application.analysis_execution import AnalyzerSelection
from app.core.ai_provider_cipher import FernetAiProviderSecretCipher
from app.core.config import Settings
from app.infrastructure.ai_cli import (
    AnalysisCliError,
    ClaudeCliVideoAnalyzer,
    CliAdapterConfig,
    CodexAppServerVideoAnalyzer,
    preflight,
)
from app.infrastructure.ai_cli.environment import minimum_host_environment


@dataclass(frozen=True, slots=True)
class AnalyzerRuntime:
    analyzer: CodexAppServerVideoAnalyzer | ClaudeCliVideoAnalyzer
    provider: str
    model: str
    cli_version: str


class ConfiguredAnalyzerResolver:
    """Resolve the active DB profile for every task and cache its CLI adapter."""

    def __init__(
        self,
        settings: Settings,
        repository: AiProviderRepository,
        cipher: FernetAiProviderSecretCipher,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._cipher = cipher
        self._cached_stamp: tuple[str, object] | None = None
        self._cached: AnalyzerSelection | None = None

    async def resolve(self) -> AnalyzerSelection:
        if not self._settings.analysis_enabled:
            raise AnalysisCliError("analysis_cli_unavailable")
        profile = await self._repository.get_active_profile()
        if profile is None:
            raise AnalysisCliError("analysis_cli_unavailable")
        stamp = (profile.key, profile.updated_at)
        if self._cached_stamp == stamp and self._cached is not None:
            return self._cached
        runtime = _build_profile_analyzer(self._settings, profile, self._cipher)
        selection = AnalyzerSelection(
            analyzer=runtime.analyzer,
            provider=profile.key,
            model=runtime.model,
            cli_version=runtime.cli_version,
        )
        self._cached_stamp = stamp
        self._cached = selection
        return selection


def build_video_analyzer(
    settings: Settings,
) -> AnalyzerRuntime:
    if not settings.analysis_enabled:
        raise AnalysisCliError("analysis_cli_unavailable")
    environment = authentication_environment()
    provider = settings.analysis_cli_provider
    binary, model = _provider_values(settings)
    capabilities = preflight(
        provider,
        cli_binary=binary,
        ffmpeg_binary=settings.analysis_ffmpeg_binary,
        ffprobe_binary=settings.analysis_ffprobe_binary,
        environment=environment,
    )
    config = CliAdapterConfig(
        binary=capabilities.binary,
        model=model,
        ffmpeg=capabilities.ffmpeg,
        ffprobe=capabilities.ffprobe,
        timeout_seconds=settings.analysis_timeout_seconds,
        max_stdout_bytes=settings.analysis_max_stdout_bytes,
        max_stderr_bytes=settings.analysis_max_stderr_bytes,
        max_workspace_bytes=settings.analysis_max_workspace_bytes,
        max_workspace_files=settings.analysis_max_workspace_files,
        max_frames=settings.analysis_max_frames,
        max_image_bytes=settings.analysis_max_image_bytes,
        workspace_poll_seconds=settings.analysis_workspace_poll_seconds,
        terminate_grace_seconds=settings.analysis_terminate_grace_seconds,
        max_turns=settings.analysis_claude_max_turns,
    )
    analyzer: CodexAppServerVideoAnalyzer | ClaudeCliVideoAnalyzer
    if provider == "codex":
        analyzer = CodexAppServerVideoAnalyzer(config)
    else:
        analyzer = ClaudeCliVideoAnalyzer(config)
    return AnalyzerRuntime(analyzer, provider, model, capabilities.version)


def _build_profile_analyzer(
    settings: Settings,
    profile: AiProviderProfile,
    cipher: FernetAiProviderSecretCipher,
) -> AnalyzerRuntime:
    provider = profile.engine.value
    binary = (
        settings.analysis_codex_binary
        if profile.engine is AiProviderEngine.CODEX
        else settings.analysis_claude_binary
    )
    environment = authentication_environment()
    extra_environment: tuple[tuple[str, str], ...] = ()
    provider_arguments: tuple[str, ...] = ()
    if profile.auth_mode is AiProviderAuthMode.API_KEY:
        if (
            profile.credential_ciphertext is None
            or profile.credential_key_id is None
            or profile.base_url is None
        ):
            raise AnalysisCliError("analysis_cli_not_authenticated")
        secret = cipher.decrypt(
            profile.key,
            profile.credential_ciphertext,
            profile.credential_key_id,
        )
        if profile.engine is AiProviderEngine.CODEX:
            extra_environment = (("VIDEO_ANALYSIS_PROVIDER_KEY", secret),)
            provider_arguments = _codex_provider_arguments(profile)
        else:
            extra_environment = (
                ("ANTHROPIC_API_KEY", secret),
                ("ANTHROPIC_BASE_URL", profile.base_url),
            )
    capabilities = preflight(
        provider,
        cli_binary=binary,
        ffmpeg_binary=settings.analysis_ffmpeg_binary,
        ffprobe_binary=settings.analysis_ffprobe_binary,
        environment=environment,
        verify_authentication=profile.auth_mode is AiProviderAuthMode.HOST_LOGIN,
    )
    config = _adapter_config(
        settings,
        capabilities.binary,
        profile.model,
        capabilities.ffmpeg,
        capabilities.ffprobe,
        extra_environment=extra_environment,
        provider_arguments=provider_arguments,
    )
    analyzer: CodexAppServerVideoAnalyzer | ClaudeCliVideoAnalyzer
    if profile.engine is AiProviderEngine.CODEX:
        analyzer = CodexAppServerVideoAnalyzer(config)
    else:
        analyzer = ClaudeCliVideoAnalyzer(config)
    return AnalyzerRuntime(analyzer, profile.key, profile.model, capabilities.version)


def _codex_provider_arguments(profile: AiProviderProfile) -> tuple[str, ...]:
    assert profile.base_url is not None
    values: tuple[tuple[str, object], ...] = (
        ("model_provider", "video_analysis"),
        ("model_providers.video_analysis.name", profile.display_name),
        ("model_providers.video_analysis.base_url", profile.base_url),
        ("model_providers.video_analysis.env_key", "VIDEO_ANALYSIS_PROVIDER_KEY"),
        ("model_providers.video_analysis.wire_api", "responses"),
    )
    return tuple(
        item for key, value in values for item in ("-c", f"{key}={json.dumps(value)}")
    )


def _adapter_config(
    settings: Settings,
    binary: Path,
    model: str,
    ffmpeg: Path,
    ffprobe: Path,
    *,
    extra_environment: tuple[tuple[str, str], ...] = (),
    provider_arguments: tuple[str, ...] = (),
) -> CliAdapterConfig:
    return CliAdapterConfig(
        binary=binary,
        model=model,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        timeout_seconds=settings.analysis_timeout_seconds,
        max_stdout_bytes=settings.analysis_max_stdout_bytes,
        max_stderr_bytes=settings.analysis_max_stderr_bytes,
        max_workspace_bytes=settings.analysis_max_workspace_bytes,
        max_workspace_files=settings.analysis_max_workspace_files,
        max_frames=settings.analysis_max_frames,
        max_image_bytes=settings.analysis_max_image_bytes,
        workspace_poll_seconds=settings.analysis_workspace_poll_seconds,
        terminate_grace_seconds=settings.analysis_terminate_grace_seconds,
        max_turns=settings.analysis_claude_max_turns,
        extra_environment=extra_environment,
        provider_arguments=provider_arguments,
    )


def authentication_environment() -> dict[str, str]:
    # Build from an explicit allowlist so inherited API credentials can never
    # reach the CLI. Windows still needs its core runtime variables for DNS
    # and process creation, so keep that non-secret allowlist in one place.
    return minimum_host_environment(os.environ.get("PATH", "/usr/bin:/bin"))


def _provider_values(settings: Settings) -> tuple[Path, str]:
    if settings.analysis_cli_provider == "codex":
        return settings.analysis_codex_binary, settings.analysis_codex_model
    return settings.analysis_claude_binary, settings.analysis_claude_model
