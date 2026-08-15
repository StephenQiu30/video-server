from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from app.domain.downloads import Container
from app.domain.providers import ProviderAccessMode
from app.runner.command_support import child_environment, json_object
from app.runner.errors import RunnerFailure
from app.runner.process import ProcessResult, ProcessTimeoutError
from app.runner.provider_errors import classify_provider_failure
from app.runner.provider_registry import provider_profile
from app.runner.provider_urls import provider_command_args, provider_request_url
from app.runner.settings import RunnerSettings
from app.runner.workspace_monitor import (
    WorkspaceLimitExceeded,
    run_with_workspace_limit,
)

_YTDLP_PLUGIN_ROOT = Path(__file__).resolve().parent
_REMOTE_PROBE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)


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

    async def inspect(
        self, url: str, cwd: Path, *, cookie_jar: Path | None = None
    ) -> dict[str, Any]:
        egress_proxy = self._egress_proxy(url)
        command: tuple[str, ...] = (
            *self._ytdlp_base(egress_proxy, url, cookie_jar),
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
            egress_proxy=egress_proxy,
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
        url: str,
        provider_id: str,
        output: Path,
        cwd: Path,
        *,
        cookie_jar: Path | None = None,
    ) -> None:
        egress_proxy = self._egress_proxy(url)
        command = (
            *self._ytdlp_base(egress_proxy, url, cookie_jar),
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
            egress_proxy=egress_proxy,
        )
        if not output.is_file() or output.is_symlink():
            raise RunnerFailure("download_failed", status=502)

    async def download_probe_sample(
        self,
        url: str,
        provider_id: str,
        output: Path,
        cwd: Path,
        *,
        cookie_jar: Path | None = None,
    ) -> None:
        egress_proxy = self._egress_proxy(url)
        command = (
            *self._ytdlp_base(egress_proxy, url, cookie_jar),
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
            egress_proxy=egress_proxy,
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
            provider_failure = classify_provider_failure(command, result.stderr)
            if provider_failure is not None:
                code, status = provider_failure
                raise RunnerFailure(code, status=status)
            raise RunnerFailure(failure_code, status=502)
        return result

    def _egress_proxy(self, url: str) -> str:
        return self._settings.egress_proxy_for(provider_profile(url).key)

    def _ytdlp_base(
        self,
        egress_proxy: str,
        url: str,
        cookie_jar: Path | None,
    ) -> tuple[str, ...]:
        profile = provider_profile(url)
        if (
            cookie_jar is not None
            and ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes
        ):
            raise RunnerFailure("provider_session_not_allowed", status=422)
        command: tuple[str, ...] = (
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
            "--js-runtimes",
            self._settings.runner_ytdlp_js_runtime,
            "--proxy",
            egress_proxy,
        )
        if cookie_jar is not None:
            command += ("--cookies", str(cookie_jar))
        if profile.key == "tiktok" and self._settings.runner_tiktok_device_id:
            command += (
                "--extractor-args",
                f"tiktok:device_id={self._settings.runner_tiktok_device_id}",
            )
        if profile.key == "youtube" and self._settings.runner_youtube_pot_base_url:
            command += (
                "--extractor-args",
                "youtube:player_client=default,mweb",
                "--extractor-args",
                "youtubepot-bgutilhttp:base_url="
                f"{self._settings.runner_youtube_pot_base_url}",
            )
        return command
