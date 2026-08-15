from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from app.application.analysis import AnalysisJobSnapshot
from app.application.analysis_execution import (
    AnalysisExecution,
    AnalysisScreenplaySource,
    LocalScreenplayArtifact,
    ScreenplayAnalysisExecutor,
    ScreenplayAnalysisRequest,
    ScreenplayAnalysisSynthesisRequest,
    ScreenplayAnalyzerSelection,
    ScreenplaySceneSource,
    VideoAnalysisRequest,
)

from .fakes import NOW, FakeLoader, FakeRepository, running_job, settings
from .fixtures import valid_mapping

SCREENPLAY_TEXT = "INT. EDITING ROOM - NIGHT\n\n林舟发现结局素材消失了。\n"


class ScreenplayRepository(FakeRepository):
    def __init__(
        self, job: AnalysisJobSnapshot, source: AnalysisScreenplaySource
    ) -> None:
        super().__init__(job)
        self.screenplay_source = source

    async def get_screenplay_source(
        self, job: AnalysisJobSnapshot, now: datetime
    ) -> AnalysisScreenplaySource:
        del job, now
        return self.screenplay_source


class FakeScreenplayLoader:
    def __init__(self, root: Path, text: str = SCREENPLAY_TEXT) -> None:
        self.root = root
        self.text = text
        self.calls = 0
        self.cleaned = False

    async def materialize(
        self, source: AnalysisScreenplaySource, *, job_id: UUID, attempt: int
    ) -> LocalScreenplayArtifact:
        del source, job_id, attempt
        self.calls += 1
        screenplay = self.root / "input" / "screenplay.md"
        screenplay.parent.mkdir(parents=True)
        screenplay.write_text(self.text, encoding="utf-8")
        return LocalScreenplayArtifact(self.root, screenplay)

    async def cleanup(self, local: LocalScreenplayArtifact) -> None:
        del local
        self.cleaned = True


class FakeScreenplayAnalyzer:
    def __init__(self, output: object) -> None:
        self.output = output
        self.requests: list[ScreenplayAnalysisRequest] = []
        self.synthesis_requests: list[ScreenplayAnalysisSynthesisRequest] = []

    async def analyze_screenplay(self, request: ScreenplayAnalysisRequest) -> object:
        self.requests.append(request)
        return self.output

    async def synthesize_screenplay_analysis(
        self, request: ScreenplayAnalysisSynthesisRequest
    ) -> object:
        self.synthesis_requests.append(request)
        assert isinstance(self.output, dict)
        return {key: value for key, value in self.output.items() if key != "scenes"}


class FakeScreenplayResolver:
    def __init__(self, analyzer: FakeScreenplayAnalyzer) -> None:
        self.analyzer = analyzer

    async def resolve_screenplay(self) -> ScreenplayAnalyzerSelection:
        return ScreenplayAnalyzerSelection(
            analyzer=self.analyzer,
            provider="controlled",
            model="controlled",
            cli_version="controlled",
        )


class FakeVideoAnalyzer:
    async def analyze(self, request: VideoAnalysisRequest) -> object:
        del request
        return valid_mapping()


def screenplay_job_and_source(
    *, character_count: int | None = None
) -> tuple[AnalysisJobSnapshot, AnalysisScreenplaySource]:
    digest = hashlib.sha256(SCREENPLAY_TEXT.encode()).hexdigest()
    document_id = uuid4()
    job = replace(
        running_job(),
        artifact_id=None,
        document_id=document_id,
        input_kind="screenplay",
        result_contract="screenplay-analysis",
        input_sha256=digest,
        skill_id="screenplay-analysis",
        skill_instructions="分析结构、人物、场景和对白，并引用原文场景。",
    )
    count = character_count if character_count is not None else len(SCREENPLAY_TEXT)
    source = AnalysisScreenplaySource(
        artifact_id=uuid4(),
        document_id=document_id,
        owner_hash=job.owner_hash,
        bucket="video-artifacts",
        object_key=f"documents/{document_id}/1/screenplay.md",
        sha256=digest,
        size_bytes=len(SCREENPLAY_TEXT.encode()),
        character_count=count,
        detected_language="mixed",
        expires_at=NOW + timedelta(hours=1),
        scenes=(ScreenplaySceneSource("scene-1", 0, min(len(SCREENPLAY_TEXT), count)),),
    )
    return job, source


def build_screenplay_execution(
    repository: ScreenplayRepository,
    video_loader: FakeLoader,
    screenplay_loader: FakeScreenplayLoader,
    analyzer: FakeScreenplayAnalyzer,
    *,
    maximum: int = 120_000,
    max_chunks: int = 128,
) -> AnalysisExecution:
    screenplay = ScreenplayAnalysisExecutor(
        repository=repository,
        loader=screenplay_loader,
        resolver=FakeScreenplayResolver(analyzer),
        clock=lambda: NOW,
        max_single_call_characters=maximum,
        max_chunks=max_chunks,
    )
    return AnalysisExecution(
        repository=repository,
        loader=video_loader,
        analyzer=FakeVideoAnalyzer(),
        screenplay_executor=screenplay,
        clock=lambda: NOW,
        settings=settings(),
    )
