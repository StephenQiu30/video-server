from __future__ import annotations

from pathlib import Path

from app.application.analysis_execution import VideoAnalysisRequest
from app.runner.process import ProcessSupervisor, ProcessTimeoutError

from .codex_mcp import video_observer_arguments
from .codex_policy import codex_permission_arguments
from .config import CliAdapterConfig
from .environment import child_environment
from .errors import AnalysisCliError, classify_cli_failure
from .prompt import analysis_prompt
from .schema import analysis_output_schema
from .workspace import prepare_job_files, read_result, run_with_workspace_policy


class CodexCliVideoAnalyzer:
    def __init__(
        self,
        config: CliAdapterConfig,
        *,
        supervisor: ProcessSupervisor | None = None,
    ) -> None:
        self._config = config
        self._supervisor = supervisor or ProcessSupervisor(
            stdout_limit_bytes=config.max_stdout_bytes,
            stderr_limit_bytes=config.max_stderr_bytes,
            terminate_grace_seconds=config.terminate_grace_seconds,
        )

    async def analyze(self, request: VideoAnalysisRequest) -> object:
        schema = analysis_output_schema(request.output_language)
        prompt = analysis_prompt(
            request,
            ffmpeg=str(self._config.ffmpeg),
            ffprobe=str(self._config.ffprobe),
            video_observer=True,
        )
        files = prepare_job_files(request, schema, prompt)
        argv = self._argv(
            files.root,
            files.schema,
            files.result,
            request.duration_ms,
        )
        try:
            result = await run_with_workspace_policy(
                self._supervisor.run(
                    argv,
                    cwd=files.root,
                    timeout_seconds=self._config.timeout_seconds,
                    env=child_environment(self._config, files.root),
                    input_bytes=prompt.encode(),
                ),
                root=files.root,
                config=self._config,
            )
        except ProcessTimeoutError as exc:
            raise AnalysisCliError("analysis_cli_timeout") from exc
        except OSError as exc:
            raise AnalysisCliError("analysis_cli_unavailable") from exc
        if result.stdout_truncated or result.stderr_truncated:
            raise AnalysisCliError("analysis_resource_limit")
        if result.returncode != 0:
            raise classify_cli_failure(result.stderr)
        return read_result(
            files.result,
            root=files.root,
            maximum=self._config.max_stdout_bytes,
        )

    def _argv(
        self,
        root: Path,
        schema: Path,
        result: Path,
        duration_ms: int,
    ) -> tuple[str, ...]:
        return (
            str(self._config.binary),
            "--ask-for-approval",
            "never",
            "--strict-config",
            "exec",
            "--cd",
            str(root),
            "--skip-git-repo-check",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            *self._config.provider_arguments,
            *video_observer_arguments(
                self._config,
                root=root,
                duration_ms=duration_ms,
            ),
            *codex_permission_arguments(),
            "--model",
            self._config.model,
            "--output-schema",
            str(schema),
            "--output-last-message",
            str(result),
            "-c",
            'web_search="disabled"',
            "-",
        )
