from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import (
    AnalysisResultContract,
    AnalysisStage,
    parse_screenplay_analysis_result,
)

from .errors import AnalysisArtifactError, AnalysisExecutionError
from .models import (
    SCREENPLAY_SINGLE_CALL_SCENE_LIMIT,
    AnalysisExecutionOutput,
    LocalScreenplayArtifact,
    ScreenplayAnalysisRequest,
)
from .monitor import AnalysisLeaseMonitor
from .ports import (
    AnalysisExecutionRepository,
    Clock,
    ScreenplayAnalyzerResolver,
    ScreenplayAnalyzerSelection,
    ScreenplayArtifactLoader,
)


class ScreenplayAnalysisExecutor:
    def __init__(
        self,
        *,
        repository: AnalysisExecutionRepository,
        loader: ScreenplayArtifactLoader,
        resolver: ScreenplayAnalyzerResolver,
        clock: Clock,
        max_single_call_characters: int,
    ) -> None:
        if max_single_call_characters <= 0:
            raise ValueError("screenplay single-call limit must be positive")
        self._repository = repository
        self._loader = loader
        self._resolver = resolver
        self._clock = clock
        self._maximum = max_single_call_characters

    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput:
        if job.result_contract != AnalysisResultContract.SCREENPLAY_ANALYSIS.value:
            raise AnalysisExecutionError("analysis_cli_unsupported")
        source = await self._repository.get_screenplay_source(job, self._clock())
        if (
            source.character_count > self._maximum
            or len(source.scenes) > SCREENPLAY_SINGLE_CALL_SCENE_LIMIT
        ):
            raise AnalysisArtifactError("analysis_resource_limit")
        local: LocalScreenplayArtifact | None = None
        try:
            local = await monitor.run(
                lambda: self._loader.materialize(
                    source, job_id=job.id, attempt=job.attempt
                ),
                stage=AnalysisStage.PREPARING,
                progress=10,
            )
            text = await asyncio.to_thread(_read_screenplay, local.screenplay)
            request = ScreenplayAnalysisRequest(
                screenplay=local.screenplay,
                workspace=local.workspace,
                screenplay_text=text,
                source_scene_ids=tuple(scene.id for scene in source.scenes),
                source_language=source.detected_language,
                output_language=job.output_language,
                skill_id=job.skill_id,
                skill_instructions=job.skill_instructions,
                custom_prompt=job.custom_prompt,
            )
            selection, payload = await monitor.run(
                lambda: self._analyze(request),
                stage=AnalysisStage.ANALYZING,
                progress=70,
            )
            result = parse_screenplay_analysis_result(
                payload,
                expected_language=job.output_language,
                source_scene_ids=request.source_scene_ids,
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
        self, request: ScreenplayAnalysisRequest
    ) -> tuple[ScreenplayAnalyzerSelection, object]:
        selection = await self._resolver.resolve_screenplay()
        return selection, await selection.analyzer.analyze_screenplay(request)


def _read_screenplay(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AnalysisArtifactError("artifact_integrity_failed") from exc
