from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import partial

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisResultContract,
    AnalysisStage,
    AnalysisValidationError,
    ScreenplayRewriteChunkOutput,
    ScreenplayRewriteGlossary,
    parse_screenplay_glossary,
    parse_screenplay_rewrite_chunk,
)

from .errors import AnalysisArtifactError, AnalysisExecutionError
from .models import AnalysisExecutionOutput, LocalScreenplayArtifact
from .monitor import AnalysisLeaseMonitor
from .ports import (
    AnalysisExecutionRepository,
    Clock,
    ScreenplayArtifactLoader,
    ScreenplayRewriteAnalyzerResolver,
    ScreenplayRewriteAnalyzerSelection,
)
from .screenplay_rewrite_models import (
    ScreenplayGlossaryRequest,
    ScreenplayRewriteChunkRequest,
)
from .screenplay_rewrite_plan import (
    ScreenplayRewriteSourceChunk,
    plan_screenplay_glossary_chunks,
    plan_screenplay_rewrite,
)
from .screenplay_rewrite_result import (
    build_chunk_request,
    build_rewrite_result,
    merge_screenplay_glossaries,
    read_screenplay_text,
)


class ScreenplayRewriteExecutor:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        loader: ScreenplayArtifactLoader,
        resolver: ScreenplayRewriteAnalyzerResolver,
        clock: Clock,
        max_glossary_characters: int,
        max_chunk_characters: int,
        max_chunks: int,
        context_characters: int,
        max_output_characters: int,
        chunk_call_attempts: int,
        chunk_retry_delay_seconds: float,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        limits = (
            max_glossary_characters,
            max_chunk_characters,
            max_chunks,
            context_characters,
            max_output_characters,
        )
        if (
            any(
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
                for value in limits
            )
            or max_chunks > 512
            or isinstance(chunk_call_attempts, bool)
            or not isinstance(chunk_call_attempts, int)
            or not 1 <= chunk_call_attempts <= 5
            or isinstance(chunk_retry_delay_seconds, bool)
            or not isinstance(chunk_retry_delay_seconds, (int, float))
            or chunk_retry_delay_seconds < 0
        ):
            raise ValueError("screenplay rewrite limits must be positive")
        self._repository = repository
        self._loader = loader
        self._resolver = resolver
        self._clock = clock
        self._glossary_limit = max_glossary_characters
        self._chunk_limit = max_chunk_characters
        self._max_chunks = max_chunks
        self._context = context_characters
        self._output_limit = max_output_characters
        self._chunk_call_attempts = chunk_call_attempts
        self._chunk_retry_delay = float(chunk_retry_delay_seconds)
        self._sleep = sleep

    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput:
        if job.result_contract != AnalysisResultContract.SCREENPLAY_REWRITE.value:
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
            plan = plan_screenplay_rewrite(
                text,
                source.scenes,
                max_chunk_characters=self._chunk_limit,
                max_chunks=self._max_chunks,
            )
            selection = await monitor.run(
                self._resolver.resolve_screenplay_rewrite,
                stage=AnalysisStage.ANALYZING,
                progress=15,
            )
            glossary = await self._glossary(
                job,
                local,
                text,
                source.detected_language,
                selection,
                monitor,
            )
            outputs = await self._rewrite_chunks(
                job, local, text, plan, glossary, selection, monitor
            )
            result = build_rewrite_result(
                source.detected_language,
                job.output_language,
                plan,
                glossary,
                outputs,
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

    async def _glossary(
        self,
        job: AnalysisJobSnapshot,
        local: LocalScreenplayArtifact,
        text: str,
        source_language: str,
        selection: ScreenplayRewriteAnalyzerSelection,
        monitor: AnalysisLeaseMonitor,
    ) -> ScreenplayRewriteGlossary:
        segments = plan_screenplay_glossary_chunks(
            text, max_chunk_characters=self._glossary_limit
        )
        glossaries: list[ScreenplayRewriteGlossary] = []
        for index, segment in enumerate(segments):
            request = ScreenplayGlossaryRequest(
                screenplay=local.screenplay,
                workspace=local.workspace,
                screenplay_text=segment,
                source_language=source_language,
                target_language=job.output_language,
                skill_id=job.skill_id,
                skill_instructions=job.skill_instructions,
                custom_prompt=job.custom_prompt,
            )
            payload = await monitor.run(
                partial(selection.analyzer.build_screenplay_glossary, request),
                stage=AnalysisStage.ANALYZING,
                progress=20 + ((index + 1) * 5 // len(segments)),
            )
            glossaries.append(
                parse_screenplay_glossary(
                    payload,
                    expected_source_language=request.source_language,
                    expected_target_language=request.target_language,
                )
            )
        return merge_screenplay_glossaries(tuple(glossaries))

    async def _rewrite_chunks(
        self,
        job: AnalysisJobSnapshot,
        local: LocalScreenplayArtifact,
        text: str,
        plan: tuple[ScreenplayRewriteSourceChunk, ...],
        glossary: ScreenplayRewriteGlossary,
        selection: ScreenplayRewriteAnalyzerSelection,
        monitor: AnalysisLeaseMonitor,
    ) -> tuple[ScreenplayRewriteChunkOutput, ...]:
        outputs: list[ScreenplayRewriteChunkOutput] = []
        total = 0
        for index, chunk in enumerate(plan):
            request = build_chunk_request(
                job, local, text, chunk, glossary, self._context
            )
            output = await monitor.run(
                partial(self._rewrite_chunk_with_recovery, selection, request),
                stage=AnalysisStage.ANALYZING,
                progress=20 + ((index + 1) * 60 // len(plan)),
            )
            total += len(output.chunk.rewritten_text)
            if total > self._output_limit:
                raise AnalysisArtifactError("analysis_resource_limit")
            outputs.append(output)
        return tuple(outputs)

    async def _rewrite_chunk_with_recovery(
        self,
        selection: ScreenplayRewriteAnalyzerSelection,
        request: ScreenplayRewriteChunkRequest,
    ) -> ScreenplayRewriteChunkOutput:
        for call_attempt in range(1, self._chunk_call_attempts + 1):
            try:
                payload = await selection.analyzer.rewrite_screenplay_chunk(request)
                return parse_screenplay_rewrite_chunk(
                    payload,
                    expected_scene_id=request.source_scene_id,
                    expected_part_no=request.part_no,
                    expected_source_sha256=request.source_sha256,
                    expected_target_language=request.target_language,
                )
            except Exception as error:
                if (
                    call_attempt >= self._chunk_call_attempts
                    or not _recoverable_chunk_error(error)
                ):
                    raise
                await self._sleep(self._chunk_retry_delay * (2 ** (call_attempt - 1)))
        raise RuntimeError("unreachable screenplay chunk recovery state")


_RECOVERABLE_CHUNK_CODES = {
    "analysis_provider_rate_limited",
    "analysis_cli_timeout",
    "analysis_cli_failed",
    "invalid_model_output",
}


def _recoverable_chunk_error(error: Exception) -> bool:
    return (
        isinstance(error, AnalysisValidationError)
        or getattr(error, "code", None) in _RECOVERABLE_CHUNK_CODES
    )
