from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.infrastructure.ai_cli import (
    AnalysisCliError,
    ClaudeCliVideoAnalyzer,
    CliAdapterConfig,
    CodexCliVideoAnalyzer,
    preflight,
)

_FORBIDDEN_AUTH = (
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
)


@dataclass(frozen=True, slots=True)
class AnalyzerRuntime:
    analyzer: CodexCliVideoAnalyzer | ClaudeCliVideoAnalyzer
    provider: str
    model: str
    cli_version: str


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
    analyzer: CodexCliVideoAnalyzer | ClaudeCliVideoAnalyzer
    if provider == "codex":
        analyzer = CodexCliVideoAnalyzer(config)
    else:
        analyzer = ClaudeCliVideoAnalyzer(config)
    return AnalyzerRuntime(analyzer, provider, model, capabilities.version)


def authentication_environment() -> dict[str, str]:
    if any(os.environ.get(name) for name in _FORBIDDEN_AUTH):
        raise AnalysisCliError("analysis_cli_not_authenticated")
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        environment["CODEX_HOME"] = codex_home
    return environment


def _provider_values(settings: Settings) -> tuple[Path, str]:
    if settings.analysis_cli_provider == "codex":
        return settings.analysis_codex_binary, settings.analysis_codex_model
    return settings.analysis_claude_binary, settings.analysis_claude_model
