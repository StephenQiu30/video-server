from __future__ import annotations

from typing import cast

from app.application.analysis_execution import (
    AnalyzerResolver,
    ScreenplayAnalyzer,
    ScreenplayAnalyzerSelection,
)
from app.infrastructure.ai_cli import AnalysisCliError


class ConfiguredScreenplayAnalyzerResolver:
    """Reuse provider selection while requiring a no-tool screenplay adapter."""

    def __init__(self, resolver: AnalyzerResolver) -> None:
        self._resolver = resolver

    async def resolve_screenplay(self) -> ScreenplayAnalyzerSelection:
        selection = await self._resolver.resolve()
        analyze = getattr(selection.analyzer, "analyze_screenplay", None)
        if not callable(analyze):
            raise AnalysisCliError("analysis_cli_unsupported")
        return ScreenplayAnalyzerSelection(
            analyzer=cast(ScreenplayAnalyzer, selection.analyzer),
            provider=selection.provider,
            model=selection.model,
            cli_version=selection.cli_version,
        )
