from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from app.domain.downloads import Container
from app.runner.command_support import child_environment, json_object
from app.runner.errors import RunnerFailure
from app.runner.process import ProcessResult, ProcessTimeoutError
from app.runner.provider_urls import provider_command_args, provider_request_url
from app.runner.settings import RunnerSettings
from app.runner.workspace_monitor import (
    WorkspaceLimitExceeded,
    run_with_workspace_limit,
)

_YTDLP_PLUGIN_ROOT = Path(__file__).resolve().parent


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

    async def inspect(self, url: str, cwd: Path) -> dict[str, Any]:
        command = (
            *self._ytdlp_base(cwd),
            "--dump-single-json",
            "--skip-download",
            *provider_command_args(url),
            "--",
            provider_request_url(url),
        )
        result = await self._run(
            command,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="inspection_failed",
        )
        return json_object(result.stdout, "invalid_inspection_response")

    async def probe_remote(self, url: str, cwd: Path) -> dict[str, Any]:
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
            url,
        )
        result = await self._run(
            command,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="inspection_failed",
        )
        return json_object(result.stdout, "invalid_inspection_response")

    async def download_stream(
        self,
        url: str,
        provider_id: str,
        output: Path,
        cwd: Path,
    ) -> None:
        command = (
            *self._ytdlp_base(cwd),
            "--format",
            provider_id,
            "--max-filesize",
            str(self._settings.runner_max_output_bytes),
            "--output",
            str(output),
            *provider_command_args(url),
            "--",
            provider_request_url(url),
        )
        await self._run(
            command,
            cwd,
            self._settings.runner_download_timeout_seconds,
            timeout_code="download_timeout",
            failure_code="download_failed",
            monitor_workspace=True,
        )
        if not output.is_file() or output.is_symlink():
            raise RunnerFailure("download_failed", status=502)

    async def download_probe_sample(
        self,
        url: str,
        provider_id: str,
        output: Path,
        cwd: Path,
    ) -> None:
        command = (
            *self._ytdlp_base(cwd),
            "--format",
            provider_id,
            "--max-filesize",
            str(self._settings.runner_max_probe_sample_bytes),
            "--output",
            str(output),
            *provider_command_args(url),
            "--",
            provider_request_url(url),
        )
        await self._run(
            command,
            cwd,
            self._settings.runner_inspect_timeout_seconds,
            timeout_code="inspection_timeout",
            failure_code="inspection_failed",
            monitor_workspace=True,
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
    ) -> ProcessResult:
        try:
            operation = self._supervisor.run(
                command,
                cwd=cwd,
                timeout_seconds=timeout,
                env=child_environment(cwd, self._settings.runner_egress_proxy),
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
            raise RunnerFailure(failure_code, status=502)
        return result

    def _ytdlp_base(self, cwd: Path) -> tuple[str, ...]:
        return (
            self._settings.runner_ytdlp_bin,
            "--ignore-config",
            "--plugin-dirs",
            str(_YTDLP_PLUGIN_ROOT),
            "--no-playlist",
            "--no-warnings",
            "--no-progress",
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            "--extractor-retries",
            "3",
            "--cookies",
            str(cwd / "provider-cookies.txt"),
            "--js-runtimes",
            self._settings.runner_ytdlp_js_runtime,
            "--proxy",
            self._settings.runner_egress_proxy,
        )
