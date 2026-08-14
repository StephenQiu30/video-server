from __future__ import annotations

import json
from pathlib import Path

from app.application.analysis_execution import ScreenplayAnalysisRequest
from app.runner.process import ProcessSupervisor, ProcessTimeoutError

from .config import CliAdapterConfig
from .environment import child_environment
from .errors import AnalysisCliError, classify_cli_failure
from .screenplay_prompt import screenplay_analysis_prompt
from .screenplay_schema import screenplay_analysis_output_schema
from .screenplay_workspace import prepare_screenplay_job_files
from .workspace import run_with_workspace_policy

_MAX_SCHEMA_BYTES = 28_000


class ClaudeCliScreenplayAnalyzer:
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

    async def analyze(self, request: ScreenplayAnalysisRequest) -> object:
        schema = screenplay_analysis_output_schema(
            request.output_language, request.source_scene_ids
        )
        schema_json = json.dumps(schema, separators=(",", ":"))
        if len(schema_json.encode()) > _MAX_SCHEMA_BYTES:
            raise AnalysisCliError("analysis_resource_limit")
        prompt = screenplay_analysis_prompt(request)
        files = prepare_screenplay_job_files(request, schema, prompt)
        environment = child_environment(self._config, files.root)
        environment["CLAUDE_CODE_SKIP_PROMPT_HISTORY"] = "1"
        try:
            result = await run_with_workspace_policy(
                self._supervisor.run(
                    self._argv(files.claude_settings, schema_json),
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
            return wrapper["structured_output"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AnalysisCliError("invalid_model_output") from exc

    def _argv(
        self,
        settings: Path,
        schema_json: str,
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
            "",
            "--disallowedTools",
            "Bash,Read,Write,Edit,WebFetch,WebSearch,Agent",
            "--permission-mode",
            "dontAsk",
            "--model",
            self._config.model,
            "--max-turns",
            "1",
            "--output-format",
            "json",
            "--json-schema",
            schema_json,
        )
