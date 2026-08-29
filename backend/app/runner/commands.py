from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from app.domain.downloads import Container
from app.runner.command_support import child_environment, json_object
from app.runner.errors import RunnerFailure
from app.runner.process import ProcessResult, ProcessTimeoutError
from app.runner.provider_errors import (
    ProviderFailureContext,
    classify_provider_failure,
)
from app.runner.provider_registry import ProviderRequest, provider_request
from app.runner.settings import RunnerSettings
from app.runner.workspace_monitor import (
    WorkspaceLimitExceeded,
    run_with_workspace_limit,
)
from app.runner.yt_dlp_commands import YtDlpCommandBuilder

_YTDLP_PLUGIN_ROOT = Path(__file__).resolve().parent
_REMOTE_PROBE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
_LOGGER = logging.getLogger(__name__)


class ProcessRunner(Protocol):
    async def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult: ...


class MediaCommands:
    def __init__(self, settings: RunnerSettings, supervisor: ProcessRunner) -> None:
        self._settings = settings
        self._supervisor = supervisor
        self._ytdlp = YtDlpCommandBuilder(settings, _YTDLP_PLUGIN_ROOT)

    async def inspect(
        self,
        source: str | ProviderRequest,
        cwd: Path,
        *,
        cookie_jar: Path | None = None,
    ) -> dict[str, Any]:
        command = self._ytdlp.inspect(source, cookie_jar=cookie_jar)
        result = await self._run(
            command.argv,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="inspection_failed",
            egress_proxy=command.egress_proxy,
            failure_context=command.failure_context,
        )
        return json_object(result.stdout, "invalid_inspection_response")

    async def probe_remote(
        self,
        url: str,
        cwd: Path,
        *,
        referer: str | None = None,
    ) -> dict[str, Any]:
        egress_proxy = self._egress_proxy(referer or url)
        command = (
            self._settings.runner_ffprobe_bin,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            "-protocol_whitelist",
            "http,https,tcp,tls,crypto,httpproxy",
            "-user_agent",
            _REMOTE_PROBE_USER_AGENT,
            "-referer",
            referer or url,
            url,
        )
        result = await self._run(
            command,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="inspection_failed",
            egress_proxy=egress_proxy,
        )
        return json_object(result.stdout, "invalid_inspection_response")

    async def download_stream(
        self,
        source: str | ProviderRequest,
        provider_id: str,
        output: Path,
        cwd: Path,
        *,
        cookie_jar: Path | None = None,
        info_json: Path | None = None,
    ) -> None:
        command = self._ytdlp.download(
            source,
            provider_id,
            output,
            max_bytes=self._settings.runner_max_output_bytes,
            cookie_jar=cookie_jar,
            info_json=info_json,
        )
        await self._run(
            command.argv,
            cwd,
            self._settings.runner_download_timeout_seconds,
            timeout_code="download_timeout",
            failure_code="download_failed",
            monitor_workspace=True,
            egress_proxy=command.egress_proxy,
            failure_context=command.failure_context,
        )
        if not output.is_file() or output.is_symlink():
            raise RunnerFailure("download_failed", status=502)

    async def download_probe_sample(
        self,
        source: str | ProviderRequest,
        provider_id: str,
        output: Path,
        cwd: Path,
        *,
        cookie_jar: Path | None = None,
    ) -> None:
        command = self._ytdlp.download(
            source,
            provider_id,
            output,
            max_bytes=self._settings.runner_max_probe_sample_bytes,
            cookie_jar=cookie_jar,
        )
        await self._run(
            command.argv,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="inspection_failed",
            monitor_workspace=True,
            egress_proxy=command.egress_proxy,
            failure_context=command.failure_context,
        )
        if not output.is_file() or output.is_symlink():
            raise RunnerFailure("inspection_failed", status=502)

    async def remux(
        self,
        inputs: tuple[Path, ...],
        output: Path,
        container: Container,
        cwd: Path,
    ) -> None:
        command: list[str] = [
            self._settings.runner_ffmpeg_bin,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
        ]
        for source in inputs:
            command.extend(
                ("-protocol_whitelist", "file,crypto,data", "-i", str(source))
            )
        command.extend(("-map", "0:v:0"))
        command.extend(("-map", "0:a:0" if len(inputs) == 1 else "1:a:0"))
        command.extend(("-c", "copy", "-map_metadata", "-1"))
        command.extend(("-f", container.value, str(output)))
        await self._run(
            command,
            cwd,
            self._settings.runner_download_timeout_seconds,
            timeout_code="download_timeout",
            failure_code="remux_failed",
            monitor_workspace=True,
        )

    async def probe(self, artifact: Path, cwd: Path) -> dict[str, Any]:
        command = (
            self._settings.runner_ffprobe_bin,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            "-protocol_whitelist",
            "file,crypto,data",
            str(artifact),
        )
        result = await self._run(
            command,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="media_validation_failed",
        )
        return json_object(result.stdout, "media_validation_failed")

    async def _run(
        self,
        command: Sequence[str],
        cwd: Path,
        timeout: float,
        *,
        timeout_code: str,
        failure_code: str,
        monitor_workspace: bool = False,
        egress_proxy: str | None = None,
        failure_context: ProviderFailureContext | None = None,
    ) -> ProcessResult:
        selected_proxy = egress_proxy or self._settings.runner_egress_proxy
        try:
            operation = self._supervisor.run(
                command,
                cwd=cwd,
                timeout_seconds=timeout,
                env=child_environment(cwd, selected_proxy),
            )
            if monitor_workspace:
                result = await run_with_workspace_limit(
                    operation,
                    root=cwd,
                    max_bytes=self._settings.runner_max_workspace_bytes,
                    poll_interval_seconds=(
                        self._settings.runner_workspace_poll_interval_seconds
                    ),
                )
            else:
                result = await operation
        except ProcessTimeoutError as exc:
            raise RunnerFailure(timeout_code, status=504) from exc
        except WorkspaceLimitExceeded as exc:
            raise RunnerFailure("workspace_limit_exceeded", status=413) from exc
        except OSError as exc:
            raise RunnerFailure("runner_dependency_unavailable", status=503) from exc
        if result.returncode != 0:
            provider_failure = (
                classify_provider_failure(failure_context, result.stderr)
                if failure_context is not None
                else None
            )
            if provider_failure is not None:
                code, status = provider_failure
                _log_command_failure(
                    operation=failure_code,
                    provider=(
                        failure_context.provider_key
                        if failure_context is not None
                        else None
                    ),
                    code=code,
                    returncode=result.returncode,
                    stderr_truncated=result.stderr_truncated,
                )
                raise RunnerFailure(code, status=status)
            _log_command_failure(
                operation=failure_code,
                provider=(
                    failure_context.provider_key
                    if failure_context is not None
                    else None
                ),
                code=failure_code,
                returncode=result.returncode,
                stderr_truncated=result.stderr_truncated,
            )
            raise RunnerFailure(failure_code, status=502)
        return result

    def _egress_proxy(self, url: str) -> str:
        return self._settings.egress_proxy_for(provider_request(url).profile.key)


def _log_command_failure(
    *,
    operation: str,
    provider: str | None,
    code: str,
    returncode: int,
    stderr_truncated: bool,
) -> None:
    _LOGGER.warning(
        "runner command failed operation=%s provider=%s code=%s "
        "returncode=%s stderr_truncated=%s",
        operation,
        provider or "internal",
        code,
        returncode,
        stderr_truncated,
    )
