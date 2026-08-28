from __future__ import annotations

from app.application.analysis_execution import (
    ScreenplayAnalysisRequest,
    ScreenplayAnalysisSynthesisRequest,
    ScreenplayGlossaryRequest,
    ScreenplayRewriteChunkRequest,
    VideoAnalysisRequest,
)

from .codex_app_server_client import CodexAppServerClient
from .codex_app_server_protocol import CodexAppServerInvoker
from .codex_screenplay import CodexAppServerScreenplayAnalyzer
from .config import CliAdapterConfig
from .prompt import analysis_prompt
from .schema import analysis_output_schema
from .workspace import prepare_job_files, run_with_workspace_policy


class CodexAppServerVideoAnalyzer:
    def __init__(
        self,
        config: CliAdapterConfig,
        *,
        client: CodexAppServerInvoker | None = None,
    ) -> None:
        self._config = config
        self._client = client or CodexAppServerClient(config)
        self._screenplay = CodexAppServerScreenplayAnalyzer(config, client=self._client)

    async def analyze(self, request: VideoAnalysisRequest) -> object:
        schema = analysis_output_schema(
            request.output_language, request.result_contract
        )
        prompt = analysis_prompt(
            request,
            ffmpeg=str(self._config.ffmpeg),
            ffprobe=str(self._config.ffprobe),
            video_observer=True,
        )
        files = prepare_job_files(request, schema, prompt)
        return await run_with_workspace_policy(
            self._client.invoke(
                root=files.root,
                prompt=prompt,
                schema=schema,
                duration_ms=request.duration_ms,
            ),
            root=files.root,
            config=self._config,
        )

    async def analyze_screenplay(self, request: ScreenplayAnalysisRequest) -> object:
        return await self._screenplay.analyze(request)

    async def synthesize_screenplay_analysis(
        self, request: ScreenplayAnalysisSynthesisRequest
    ) -> object:
        return await self._screenplay.synthesize(request)

    async def build_screenplay_glossary(
        self, request: ScreenplayGlossaryRequest
    ) -> object:
        return await self._screenplay.build_glossary(request)

    async def rewrite_screenplay_chunk(
        self, request: ScreenplayRewriteChunkRequest
    ) -> object:
        return await self._screenplay.rewrite_chunk(request)
