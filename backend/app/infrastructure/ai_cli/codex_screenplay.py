from __future__ import annotations

import json

from app.application.analysis_execution import (
    ScreenplayAnalysisRequest,
    ScreenplayAnalysisSynthesisRequest,
    ScreenplayGlossaryRequest,
    ScreenplayRewriteChunkRequest,
)

from .codex_app_server_client import CodexAppServerClient
from .codex_app_server_protocol import CodexAppServerInvoker
from .config import CliAdapterConfig
from .screenplay_prompt import (
    screenplay_analysis_prompt,
    screenplay_analysis_synthesis_prompt,
)
from .screenplay_rewrite_prompt import (
    screenplay_glossary_prompt,
    screenplay_rewrite_chunk_prompt,
)
from .screenplay_rewrite_schema import (
    screenplay_glossary_output_schema,
    screenplay_rewrite_chunk_output_schema,
)
from .screenplay_schema import (
    screenplay_analysis_output_schema,
    screenplay_analysis_summary_output_schema,
)
from .screenplay_workspace import (
    prepare_screenplay_call_files,
    prepare_screenplay_job_files,
)
from .workspace import JobFiles, run_with_workspace_policy


class CodexAppServerScreenplayAnalyzer:
    def __init__(
        self,
        config: CliAdapterConfig,
        *,
        client: CodexAppServerInvoker | None = None,
    ) -> None:
        self._config = config
        self._client = client or CodexAppServerClient(config)

    async def analyze(self, request: ScreenplayAnalysisRequest) -> object:
        schema = screenplay_analysis_output_schema(
            request.output_language, request.source_scene_ids
        )
        prompt = screenplay_analysis_prompt(request)
        files = prepare_screenplay_job_files(request, schema, prompt)
        return await self._invoke(files, prompt)

    async def synthesize(self, request: ScreenplayAnalysisSynthesisRequest) -> object:
        schema = screenplay_analysis_summary_output_schema(request.output_language)
        prompt = screenplay_analysis_synthesis_prompt(request)
        files = prepare_screenplay_call_files(
            workspace=request.workspace,
            screenplay=request.screenplay,
            schema=schema,
            prompt=prompt,
            manifest={
                "call": "screenplay-analysis-synthesis",
                "source_language": request.source_language,
                "source_scene_ids": list(request.source_scene_ids),
            },
        )
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
        schema = json.loads(files.schema.read_text(encoding="utf-8"))
        return await run_with_workspace_policy(
            self._client.invoke(
                root=files.root,
                prompt=prompt,
                schema=schema,
                duration_ms=None,
            ),
            root=files.root,
            config=self._config,
        )
