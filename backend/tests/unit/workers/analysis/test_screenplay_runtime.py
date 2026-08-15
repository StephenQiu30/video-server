from pathlib import Path

import pytest
from app.application.analysis_execution import AnalyzerSelection
from app.core.config import Settings
from app.workers.analysis.screenplay_runtime import build_screenplay_components

from .fakes import NOW
from .screenplay_fakes import ScreenplayRepository, screenplay_job_and_source
from .screenplay_rewrite_fakes import FakeRewriteAnalyzer


class UnusedStorage:
    async def download(self, object_key: str, target: Path) -> None:
        raise AssertionError((object_key, target))


class CompleteAnalyzer(FakeRewriteAnalyzer):
    async def analyze_screenplay(self, request: object) -> object:
        del request
        return {}

    async def synthesize_screenplay_analysis(self, request: object) -> object:
        del request
        return {}

    async def analyze(self, request: object) -> object:
        del request
        return {}


class BaseResolver:
    def __init__(self) -> None:
        self.analyzer = CompleteAnalyzer()
        self.calls = 0

    async def resolve(self) -> AnalyzerSelection:
        self.calls += 1
        return AnalyzerSelection(
            analyzer=self.analyzer,  # type: ignore[arg-type]
            provider="controlled",
            model="controlled",
            cli_version="controlled",
        )


def build_components(tmp_path: Path, enabled: bool):
    job, source = screenplay_job_and_source()
    resolver = BaseResolver()
    components = build_screenplay_components(
        Settings(
            app_env="test",
            screenplay_analysis_enabled=enabled,
            analysis_workspace_root=tmp_path,
            _env_file=None,
        ),
        storage=UnusedStorage(),
        repository=ScreenplayRepository(job, source),
        analyzer_resolver=resolver,
        clock=lambda: NOW,
    )
    return components, resolver


@pytest.mark.asyncio
async def test_screenplay_runtime_is_absent_when_feature_is_disabled(
    tmp_path: Path,
) -> None:
    components, resolver = build_components(tmp_path, False)

    await components.prepare()

    assert components.executor is None
    assert components.resolver is None
    assert resolver.calls == 0


@pytest.mark.asyncio
async def test_screenplay_runtime_preflights_analysis_and_rewrite(
    tmp_path: Path,
) -> None:
    components, resolver = build_components(tmp_path, True)

    await components.prepare()

    assert components.executor is not None
    assert components.resolver is not None
    assert resolver.calls == 2
