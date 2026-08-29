"""Builder for bounded yt-dlp commands from one resolved provider request."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.domain.providers import ProviderAccessMode
from app.runner.errors import RunnerFailure
from app.runner.provider_errors import ProviderFailureContext
from app.runner.provider_registry import ProviderRequest, provider_request
from app.runner.settings import RunnerSettings


@dataclass(frozen=True, slots=True)
class BuiltYtDlpCommand:
    argv: tuple[str, ...]
    request: ProviderRequest
    egress_proxy: str
    authenticated: bool

    @property
    def failure_context(self) -> ProviderFailureContext:
        return ProviderFailureContext(
            provider_key=self.request.profile.key,
            source_url=self.request.source_url,
            authenticated=self.authenticated,
        )


class YtDlpCommandBuilder:
    def __init__(self, settings: RunnerSettings, plugin_root: Path) -> None:
        self._settings = settings
        self._plugin_root = plugin_root

    def inspect(
        self,
        source: str | ProviderRequest,
        *,
        cookie_jar: Path | None,
    ) -> BuiltYtDlpCommand:
        request = self._resolve(source)
        return self._build(
            request,
            ("--dump-single-json", "--skip-download"),
            cookie_jar=cookie_jar,
        )

    def download(
        self,
        source: str | ProviderRequest,
        provider_id: str,
        output: Path,
        *,
        max_bytes: int,
        cookie_jar: Path | None,
        info_json: Path | None = None,
    ) -> BuiltYtDlpCommand:
        request = self._resolve(source)
        operation_args: tuple[str, ...] = (
            "--format",
            provider_id,
            "--max-filesize",
            str(max_bytes),
            "--output",
            str(output),
        )
        if info_json is not None:
            operation_args += ("--load-info-json", str(info_json))
        return self._build(
            request,
            operation_args,
            cookie_jar=cookie_jar,
            include_source=info_json is None,
        )

    def _build(
        self,
        request: ProviderRequest,
        operation_args: tuple[str, ...],
        *,
        cookie_jar: Path | None,
        include_source: bool = True,
    ) -> BuiltYtDlpCommand:
        profile = request.profile
        if (
            cookie_jar is not None
            and ProviderAccessMode.OPERATOR_MANAGED not in profile.access_modes
        ):
            raise RunnerFailure("provider_session_not_allowed", status=422)
        egress_proxy = self._settings.egress_proxy_for(profile.key)
        command: tuple[str, ...] = (
            self._settings.runner_ytdlp_bin,
            "--ignore-config",
            "--plugin-dirs",
            str(self._plugin_root),
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
        command += (*operation_args, *profile.command_args_for(self._settings))
        if include_source:
            command += ("--", request.request_url)
        return BuiltYtDlpCommand(
            argv=command,
            request=request,
            egress_proxy=egress_proxy,
            authenticated=cookie_jar is not None,
        )

    @staticmethod
    def _resolve(source: str | ProviderRequest) -> ProviderRequest:
        return provider_request(source) if isinstance(source, str) else source
