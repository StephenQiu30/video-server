from __future__ import annotations

from dataclasses import dataclass

from app.application.analysis_execution import (
    ScreenplayAnalysisExecutor,
    ScreenplayExecutionRouter,
    ScreenplayRewriteExecutor,
)
from app.application.analysis_execution.ports import (
    AnalysisExecutionRepository,
    AnalyzerResolver,
    Clock,
)
from app.core.config import Settings

from .screenplay_artifacts import (
    LocalScreenplayArtifactLoader,
    ScreenplayStorage,
)
from .screenplay_providers import ConfiguredScreenplayAnalyzerResolver


@dataclass(frozen=True, slots=True)
class ScreenplayWorkerComponents:
    loader: LocalScreenplayArtifactLoader
    resolver: ConfiguredScreenplayAnalyzerResolver | None
    executor: ScreenplayExecutionRouter | None

    async def prepare(self) -> None:
        await self.loader.prepare_root()
        if self.resolver is not None:
            await self.resolver.resolve_screenplay()
            await self.resolver.resolve_screenplay_rewrite()


def build_screenplay_components(
    settings: Settings,
    *,
    storage: ScreenplayStorage,
    repository: AnalysisExecutionRepository,
    analyzer_resolver: AnalyzerResolver,
    clock: Clock,
) -> ScreenplayWorkerComponents:
    loader = LocalScreenplayArtifactLoader(
        storage,
        workspace_root=settings.analysis_workspace_root,
        bucket=settings.minio_bucket,
        max_source_bytes=settings.analysis_max_screenplay_bytes,
    )
    if not settings.screenplay_analysis_enabled:
        return ScreenplayWorkerComponents(loader, None, None)
    resolver = ConfiguredScreenplayAnalyzerResolver(analyzer_resolver)
    analysis = ScreenplayAnalysisExecutor(
        repository=repository,
        loader=loader,
        resolver=resolver,
        clock=clock,
        max_single_call_characters=settings.analysis_screenplay_single_call_characters,
        max_chunks=settings.analysis_max_screenplay_rewrite_chunks,
        max_synthesis_bytes=settings.analysis_max_stdout_bytes,
    )
    rewrite = ScreenplayRewriteExecutor(
        repository=repository,
        loader=loader,
        resolver=resolver,
        clock=clock,
        max_glossary_characters=(
            settings.analysis_screenplay_rewrite_glossary_chunk_characters
        ),
        max_chunk_characters=(settings.analysis_screenplay_rewrite_chunk_characters),
        max_chunks=settings.analysis_max_screenplay_rewrite_chunks,
        context_characters=(settings.analysis_screenplay_rewrite_context_characters),
        max_output_characters=(
            settings.analysis_max_screenplay_rewrite_output_characters
        ),
        chunk_call_attempts=settings.analysis_screenplay_rewrite_chunk_call_attempts,
        chunk_retry_delay_seconds=(
            settings.analysis_screenplay_rewrite_chunk_retry_delay_seconds
        ),
    )
    return ScreenplayWorkerComponents(
        loader,
        resolver,
        ScreenplayExecutionRouter(analysis=analysis, rewrite=rewrite),
    )
