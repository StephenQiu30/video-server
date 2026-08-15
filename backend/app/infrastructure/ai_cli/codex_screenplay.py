from __future__ import annotations

from pathlib import Path

from app.application.analysis_execution import (
    ScreenplayAnalysisRequest,
    ScreenplayGlossaryRequest,
    ScreenplayRewriteChunkRequest,
)
from app.runner.process import ProcessSupervisor, ProcessTimeoutError

from .codex_policy import codex_permission_arguments
from .config import CliAdapterConfig
from .environment import child_environment
from .errors import AnalysisCliError, classify_cli_failure
from .screenplay_prompt import screenplay_analysis_prompt
from .screenplay_rewrite_prompt import (
    screenplay_glossary_prompt,
    screenplay_rewrite_chunk_prompt,
)
from .screenplay_rewrite_schema import (
    screenplay_glossary_output_schema,
    screenplay_rewrite_chunk_output_schema,
)
from .screenplay_schema import screenplay_analysis_output_schema
from .screenplay_workspace import (
    prepare_screenplay_call_files,
    prepare_screenplay_job_files,
)
from .workspace import JobFiles, read_result, run_with_workspace_policy


class CodexCliScreenplayAnalyzer:
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
        prompt = screenplay_analysis_prompt(request)
        files = prepare_screenplay_job_files(request, schema, prompt)
        return await self._invoke(files, prompt)

    async def build_glossary(self, request: ScreenplayGlossaryRequest) -> object:
        schema = screenplay_glossary_output_schema(
            request.source_language, request.target_language
        )
        prompt = screenplay_glossary_prompt(request)
        files = prepare_screenplay_call_files(
            workspace=request.workspace,
            screenplay=request.screenplay,
            schema=schema,
            prompt=prompt,
            manifest={
                "call": "screenplay-glossary",
                "source_language": request.source_language,
                "target_language": request.target_language,
            },
        )
        return await self._invoke(files, prompt)

    async def rewrite_chunk(self, request: ScreenplayRewriteChunkRequest) -> object:
        schema = screenplay_rewrite_chunk_output_schema(
            source_scene_id=request.source_scene_id,
            part_no=request.part_no,
            source_sha256=request.source_sha256,
            target_language=request.target_language,
        )
        prompt = screenplay_rewrite_chunk_prompt(request)
        files = prepare_screenplay_call_files(
            workspace=request.workspace,
            screenplay=request.screenplay,
            schema=schema,
            prompt=prompt,
            manifest={
                "call": "screenplay-rewrite-chunk",
                "source_scene_id": request.source_scene_id,
                "part_no": request.part_no,
                "source_sha256": request.source_sha256,
                "target_language": request.target_language,
            },
        )
        return await self._invoke(files, prompt)

    async def _invoke(self, files: JobFiles, prompt: str) -> object:
        try:
            result = await run_with_workspace_policy(
                self._supervisor.run(
                    self._argv(files.root, files.schema, files.result),
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

    def _argv(self, root: Path, schema: Path, result: Path) -> tuple[str, ...]:
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
