from __future__ import annotations

from contextlib import suppress

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisMedia,
    AnalysisResultContract,
    AnalysisStage,
    parse_analysis_result,
)

from .models import AnalysisExecutionOutput, LocalAnalysisArtifact, VideoAnalysisRequest
from .monitor import AnalysisLeaseMonitor
from .ports import (
    AnalysisExecutionRepository,
    AnalyzerResolver,
    AnalyzerSelection,
    ArtifactLoader,
    Clock,
    VideoAnalyzer,
)


class VideoAnalysisExecutor:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        loader: ArtifactLoader,
        resolver: AnalyzerResolver,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._loader = loader
        self._resolver = resolver
        self._clock = clock

    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput:
        local: LocalAnalysisArtifact | None = None
        try:
            source = await self._repository.get_artifact_source(job, self._clock())
            local = await monitor.run(
                lambda: self._loader.materialize(
                    source, job_id=job.id, attempt=job.attempt
                ),
                stage=AnalysisStage.PREPARING,
                progress=10,
            )
            request = VideoAnalysisRequest(
                artifact=local.artifact,
                workspace=local.workspace,
                duration_ms=source.duration_ms,
                size_bytes=source.size_bytes,
                container=source.container,
                output_language=job.output_language,
                skill_id=job.skill_id,
                skill_instructions=job.skill_instructions,
                result_contract=AnalysisResultContract(job.result_contract),
                custom_prompt=job.custom_prompt,
            )
            selection, payload = await monitor.run(
                lambda: self._analyze(request),
                stage=AnalysisStage.ANALYZING,
                progress=70,
            )
            result = parse_analysis_result(
                payload,
                AnalysisMedia(
                    duration_ms=source.duration_ms,
                    container=source.container,
                    size_bytes=source.size_bytes,
                ),
                expected_language=job.output_language,
                result_contract=job.result_contract,
            )
            return AnalysisExecutionOutput(
                result=result,
                provider=selection.provider,
                model=selection.model,
                cli_version=selection.cli_version,
            )
        finally:
            if local is not None:
                with suppress(Exception):
                    await self._loader.cleanup(local)

    async def _analyze(
        self, request: VideoAnalysisRequest
    ) -> tuple[AnalyzerSelection, object]:
        selection = await self._resolver.resolve()
        return selection, await selection.analyzer.analyze(request)


class StaticAnalyzerResolver:
    def __init__(
        self,
        analyzer: VideoAnalyzer,
        *,
        provider: str,
        model: str,
        cli_version: str,
    ) -> None:
        self._selection = AnalyzerSelection(
            analyzer=analyzer,
            provider=provider,
            model=model,
            cli_version=cli_version,
        )

    async def resolve(self) -> AnalyzerSelection:
        return self._selection
