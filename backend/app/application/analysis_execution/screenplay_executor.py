from __future__ import annotations

import asyncio
from contextlib import suppress
from functools import partial

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisResultContract,
    AnalysisStage,
    ScreenplayAnalysisResult,
    parse_screenplay_analysis_result,
)

from .errors import AnalysisArtifactError, AnalysisExecutionError
from .models import (
    SCREENPLAY_SINGLE_CALL_SCENE_LIMIT,
    AnalysisExecutionOutput,
    AnalysisScreenplaySource,
    LocalScreenplayArtifact,
    ScreenplayAnalysisSynthesisRequest,
)
from .monitor import AnalysisLeaseMonitor
from .ports import (
    AnalysisExecutionRepository,
    Clock,
    ScreenplayAnalyzerResolver,
    ScreenplayAnalyzerSelection,
    ScreenplayArtifactLoader,
)
from .screenplay_analysis_plan import (
    plan_screenplay_analysis,
)
from .screenplay_analysis_result import (
    build_analysis_request,
    chunk_results_json,
    combined_analysis_payload,
)
from .screenplay_rewrite_result import read_screenplay_text


class ScreenplayAnalysisExecutor:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        loader: ScreenplayArtifactLoader,
        resolver: ScreenplayAnalyzerResolver,
        clock: Clock,
        max_single_call_characters: int,
        max_chunks: int = 128,
        max_synthesis_bytes: int = 2 * 1024**2,
    ) -> None:
        limits = (max_single_call_characters, max_chunks, max_synthesis_bytes)
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in limits
        ):
            raise ValueError("screenplay analysis limits must be positive")
        self._repository = repository
        self._loader = loader
        self._resolver = resolver
        self._clock = clock
        self._maximum = max_single_call_characters
        self._max_chunks = max_chunks
        self._max_synthesis_bytes = max_synthesis_bytes

    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput:
        if job.result_contract != AnalysisResultContract.SCREENPLAY_ANALYSIS.value:
            raise AnalysisExecutionError("analysis_cli_unsupported")
        source = await self._repository.get_screenplay_source(job, self._clock())
        local: LocalScreenplayArtifact | None = None
        try:
            local = await monitor.run(
                lambda: self._loader.materialize(
                    source, job_id=job.id, attempt=job.attempt
                ),
                stage=AnalysisStage.PREPARING,
                progress=10,
            )
            text = await asyncio.to_thread(read_screenplay_text, local.screenplay)
            if len(text) != source.character_count:
                raise AnalysisArtifactError("artifact_integrity_failed")
            selection = await monitor.run(
                self._resolver.resolve_screenplay,
                stage=AnalysisStage.ANALYZING,
                progress=15,
            )
            if _fits_single_call(
                source.character_count, len(source.scenes), self._maximum
            ):
                result = await self._single_call(
                    job, source, local, text, selection, monitor
                )
            else:
                result = await self._chunked(
                    job, source, local, text, selection, monitor
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

    async def _single_call(
        self,
        job: AnalysisJobSnapshot,
        source: AnalysisScreenplaySource,
        local: LocalScreenplayArtifact,
        text: str,
        selection: ScreenplayAnalyzerSelection,
        monitor: AnalysisLeaseMonitor,
    ) -> ScreenplayAnalysisResult:
        request = build_analysis_request(job, source, local, text, source.scenes)
        payload = await monitor.run(
            lambda: selection.analyzer.analyze_screenplay(request),
            stage=AnalysisStage.ANALYZING,
            progress=70,
        )
        return parse_screenplay_analysis_result(
            payload,
            expected_language=job.output_language,
            source_scene_ids=request.source_scene_ids,
        )

    async def _chunked(
        self,
        job: AnalysisJobSnapshot,
        source: AnalysisScreenplaySource,
        local: LocalScreenplayArtifact,
        text: str,
        selection: ScreenplayAnalyzerSelection,
        monitor: AnalysisLeaseMonitor,
    ) -> ScreenplayAnalysisResult:
        plan = plan_screenplay_analysis(
            text,
            source.scenes,
            max_chunk_characters=self._maximum,
            max_chunk_scenes=SCREENPLAY_SINGLE_CALL_SCENE_LIMIT,
            max_chunks=self._max_chunks,
        )
        results: list[ScreenplayAnalysisResult] = []
        for index, chunk in enumerate(plan):
            chunk_request = build_analysis_request(
                job, source, local, chunk.text, chunk.scenes
            )
            payload = await monitor.run(
                partial(selection.analyzer.analyze_screenplay, chunk_request),
                stage=AnalysisStage.ANALYZING,
                progress=15 + ((index + 1) * 55 // len(plan)),
            )
            results.append(
                parse_screenplay_analysis_result(
                    payload,
                    expected_language=job.output_language,
                    source_scene_ids=chunk_request.source_scene_ids,
                )
            )
        synthesis_input = chunk_results_json(tuple(results))
        if len(synthesis_input.encode()) > self._max_synthesis_bytes:
            raise AnalysisArtifactError("analysis_resource_limit")
        synthesis_request = ScreenplayAnalysisSynthesisRequest(
            screenplay=local.screenplay,
            workspace=local.workspace,
            chunk_results_json=synthesis_input,
            source_scene_ids=tuple(scene.id for scene in source.scenes),
            source_language=source.detected_language,
            output_language=job.output_language,
            skill_id=job.skill_id,
            skill_instructions=job.skill_instructions,
            custom_prompt=job.custom_prompt,
        )
        summary = await monitor.run(
            lambda: selection.analyzer.synthesize_screenplay_analysis(
                synthesis_request
            ),
            stage=AnalysisStage.ANALYZING,
            progress=85,
        )
        payload = combined_analysis_payload(summary, tuple(results))
        return parse_screenplay_analysis_result(
            payload,
            expected_language=job.output_language,
            source_scene_ids=synthesis_request.source_scene_ids,
        )


def _fits_single_call(characters: int, scenes: int, maximum: int) -> bool:
    return characters <= maximum and scenes <= SCREENPLAY_SINGLE_CALL_SCENE_LIMIT
