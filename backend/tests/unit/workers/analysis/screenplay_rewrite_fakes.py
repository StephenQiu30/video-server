from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from app.application.analysis_execution import (
    AnalysisExecution,
    ScreenplayAnalysisExecutor,
    ScreenplayExecutionRouter,
    ScreenplayGlossaryRequest,
    ScreenplayRewriteAnalyzerSelection,
    ScreenplayRewriteChunkRequest,
    ScreenplayRewriteExecutor,
)

from .fakes import NOW, FakeLoader, settings
from .screenplay_fakes import (
    FakeScreenplayAnalyzer,
    FakeScreenplayLoader,
    FakeScreenplayResolver,
    FakeVideoAnalyzer,
    ScreenplayRepository,
    screenplay_job_and_source,
)


class FakeRewriteAnalyzer:
    def __init__(self) -> None:
        self.glossary_requests: list[ScreenplayGlossaryRequest] = []
        self.chunk_requests: list[ScreenplayRewriteChunkRequest] = []
        self.invalid_call: int | None = None
        self.omit_glossary_target = False
        self.rewritten_text = "Rewritten scene part.\n"

    async def build_screenplay_glossary(
        self, request: ScreenplayGlossaryRequest
    ) -> object:
        self.glossary_requests.append(request)
        return {
            "source_language": request.source_language,
            "target_language": request.target_language,
            "terms": [
                {"source": "林舟", "target": "Lin Zhou", "category": "character"}
            ],
            "style_rules": ["Preserve screenplay formatting."],
        }

    async def rewrite_screenplay_chunk(
        self, request: ScreenplayRewriteChunkRequest
    ) -> object:
        self.chunk_requests.append(request)
        scene_id = request.source_scene_id
        if self.invalid_call == len(self.chunk_requests):
            scene_id = "scene-invented"
        prefix = ""
        if not self.omit_glossary_target:
            prefix = "Lin Zhou " * request.source_text.count("林舟")
        return {
            "source_scene_id": scene_id,
            "part_no": request.part_no,
            "source_sha256": request.source_sha256,
            "target_language": request.target_language,
            "rewritten_text": prefix + self.rewritten_text,
            "change_summary": ["Rewrote the scene in natural English."],
        }


class FakeRewriteResolver:
    def __init__(self, analyzer: FakeRewriteAnalyzer) -> None:
        self.analyzer = analyzer
        self.calls = 0

    async def resolve_screenplay_rewrite(
        self,
    ) -> ScreenplayRewriteAnalyzerSelection:
        self.calls += 1
        return ScreenplayRewriteAnalyzerSelection(
            analyzer=self.analyzer,
            provider="controlled",
            model="controlled",
            cli_version="controlled",
        )


def build_rewrite_execution(
    root: Path,
    *,
    maximum: int = 20,
    max_chunks: int = 20,
    max_output: int = 10_000,
) -> tuple[
    AnalysisExecution,
    ScreenplayRepository,
    FakeScreenplayLoader,
    FakeRewriteAnalyzer,
    FakeRewriteResolver,
]:
    job, source = screenplay_job_and_source()
    job = replace(
        job,
        result_contract="screenplay-rewrite",
        output_language="en-US",
        skill_id="screenplay-rewrite",
        skill_instructions="Rewrite the screenplay in natural English.",
    )
    repository = ScreenplayRepository(job, source)
    loader = FakeScreenplayLoader(root / "screenplay")
    analyzer = FakeRewriteAnalyzer()
    resolver = FakeRewriteResolver(analyzer)
    rewrite = ScreenplayRewriteExecutor(
        repository=repository,
        loader=loader,
        resolver=resolver,
        clock=lambda: NOW,
        max_glossary_characters=120_000,
        max_chunk_characters=maximum,
        max_chunks=max_chunks,
        context_characters=10,
        max_output_characters=max_output,
    )
    analysis = ScreenplayAnalysisExecutor(
        repository=repository,
        loader=loader,
        resolver=FakeScreenplayResolver(FakeScreenplayAnalyzer({})),
        clock=lambda: NOW,
        max_single_call_characters=120_000,
    )
    router = ScreenplayExecutionRouter(analysis=analysis, rewrite=rewrite)
    execution = AnalysisExecution(
        repository=repository,
        loader=FakeLoader(root / "video"),
        analyzer=FakeVideoAnalyzer(),
        screenplay_executor=router,
        clock=lambda: NOW,
        settings=settings(),
    )
    return execution, repository, loader, analyzer, resolver
