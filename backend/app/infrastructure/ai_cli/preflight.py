from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .errors import AnalysisCliError

CommandRunner = Callable[
    [Sequence[str], Mapping[str, str]], subprocess.CompletedProcess[str]
]


@dataclass(frozen=True, slots=True)
class CliCapabilities:
    provider: str
    binary: Path
    version: str
    ffmpeg: Path
    ffprobe: Path


def preflight(
    provider: str,
    *,
    cli_binary: str | Path,
    ffmpeg_binary: str | Path,
    ffprobe_binary: str | Path,
    environment: Mapping[str, str],
    runner: CommandRunner | None = None,
) -> CliCapabilities:
    execute = runner or _run
    binary = _resolve(cli_binary)
    ffmpeg = _resolve(ffmpeg_binary)
    ffprobe = _resolve(ffprobe_binary)
    version = _successful(execute, (str(binary), "--version"), environment)
    _successful(execute, (str(ffmpeg), "-version"), environment)
    _successful(execute, (str(ffprobe), "-version"), environment)
    if provider == "codex":
        _verify_codex(execute, binary, environment)
    elif provider == "claude":
        _verify_claude(execute, binary, environment)
    else:
        raise AnalysisCliError("analysis_cli_unsupported")
    return CliCapabilities(
        provider=provider,
        binary=binary,
        version=version.splitlines()[0],
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
    )


def _resolve(value: str | Path) -> Path:
    candidate = str(value)
    explicit = Path(candidate).expanduser()
    if explicit.is_absolute() and explicit.is_file():
        return explicit.resolve()
    resolved = shutil.which(candidate)
    if resolved is None:
        raise AnalysisCliError("analysis_cli_unavailable")
    path = Path(resolved).resolve()
    if not path.is_file():
        raise AnalysisCliError("analysis_cli_unavailable")
    return path


def _verify_codex(
    execute: CommandRunner,
    binary: Path,
    environment: Mapping[str, str],
) -> None:
    version = _successful(execute, (str(binary), "--version"), environment)
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None or tuple(map(int, match.groups())) < (0, 138, 0):
        raise AnalysisCliError("analysis_cli_unsupported")
    help_text = _successful(execute, (str(binary), "exec", "--help"), environment)
    required = ("--ephemeral", "--output-schema", "--output-last-message")
    if any(option not in help_text for option in required):
        raise AnalysisCliError("analysis_cli_unsupported")
    status = _successful(
        execute,
        (str(binary), "login", "status"),
        environment,
        failure_code="analysis_cli_not_authenticated",
    )
    normalized = status.lower()
    if "logged in" not in normalized or "chatgpt" not in normalized:
        raise AnalysisCliError("analysis_cli_not_authenticated")


def _verify_claude(
    execute: CommandRunner,
    binary: Path,
    environment: Mapping[str, str],
) -> None:
    help_text = _successful(execute, (str(binary), "--help"), environment)
    required = ("--safe-mode", "--json-schema", "--strict-mcp-config")
    if any(option not in help_text for option in required):
        raise AnalysisCliError("analysis_cli_unsupported")
    raw = _successful(
        execute,
        (str(binary), "auth", "status", "--json"),
        environment,
        failure_code="analysis_cli_not_authenticated",
    )
    try:
        status = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AnalysisCliError("analysis_cli_not_authenticated") from exc
    authenticated = (
        status.get("loggedIn") is True
        and status.get("authMethod") == "oauth_token"
        and status.get("apiProvider") == "firstParty"
    )
    if not authenticated:
        raise AnalysisCliError("analysis_cli_not_authenticated")


def _successful(
    execute: CommandRunner,
    argv: Sequence[str],
    environment: Mapping[str, str],
    *,
    failure_code: str = "analysis_cli_unavailable",
) -> str:
    try:
        result = execute(argv, environment)
    except OSError as exc:
        raise AnalysisCliError("analysis_cli_unavailable") from exc
    if result.returncode != 0:
        raise AnalysisCliError(failure_code)
    return f"{result.stdout}\n{result.stderr}".strip()


def _run(
    argv: Sequence[str],
    environment: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        env=dict(environment),
    )
