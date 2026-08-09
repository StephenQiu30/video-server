from __future__ import annotations

import json
from pathlib import Path

from app.application.analysis_execution import VideoAnalysisRequest
from app.runner.process import ProcessSupervisor, ProcessTimeoutError

from .config import CliAdapterConfig
from .environment import child_environment
from .errors import AnalysisCliError, classify_cli_failure
from .prompt import analysis_prompt
from .schema import analysis_output_schema
from .workspace import prepare_job_files, run_with_workspace_policy


class ClaudeCliVideoAnalyzer:
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
        schema = analysis_output_schema(request.schema_version, request.output_language)
        prompt = analysis_prompt(
            request,
            ffmpeg=str(self._config.ffmpeg),
            ffprobe=str(self._config.ffprobe),
        )
        files = prepare_job_files(request, schema, prompt)
        environment = child_environment(self._config, files.root)
        environment["CLAUDE_CODE_SKIP_PROMPT_HISTORY"] = "1"
        try:
            result = await run_with_workspace_policy(
                self._supervisor.run(
                    self._argv(files.root, files.claude_settings, schema),
                    cwd=files.root,
                    timeout_seconds=self._config.timeout_seconds,
                    env=environment,
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
            raise classify_cli_failure(result.stderr + result.stdout)
        try:
            wrapper = json.loads(result.stdout)
            structured = wrapper["structured_output"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AnalysisCliError("invalid_model_output") from exc
        return structured

    def _argv(
        self,
        root: Path,
        settings: Path,
        schema: dict[str, object],
    ) -> tuple[str, ...]:
        return (
            str(self._config.binary),
            "--safe-mode",
            "-p",
            "--no-session-persistence",
            "--no-chrome",
            "--disable-slash-commands",
            "--strict-mcp-config",
            "--settings",
            str(settings),
            "--tools",
            "Bash,Read",
            "--permission-mode",
            "dontAsk",
            "--allowedTools",
            f"Read({root / 'input' / 'manifest.json'})",
            "--allowedTools",
            f"Read({root / 'work'}/**)",
            "--allowedTools",
            f"Bash({self._config.ffprobe} *)",
            "--allowedTools",
            f"Bash({self._config.ffmpeg} *)",
            "--model",
            self._config.model,
            "--max-turns",
            str(self._config.max_turns),
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(schema, separators=(",", ":")),
        )
