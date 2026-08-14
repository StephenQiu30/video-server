from __future__ import annotations

from typing import Protocol

from app.application.analysis import AnalysisJobSnapshot
from app.domain.analysis import AnalysisResultContract

from .errors import AnalysisExecutionError
from .models import AnalysisExecutionOutput
from .monitor import AnalysisLeaseMonitor


class ScreenplayContractExecutor(Protocol):
    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput: ...


class ScreenplayExecutionRouter:
    def __init__(
        self,
        *,
        analysis: ScreenplayContractExecutor,
        rewrite: ScreenplayContractExecutor,
    ) -> None:
        self._executors = {
            AnalysisResultContract.SCREENPLAY_ANALYSIS.value: analysis,
            AnalysisResultContract.SCREENPLAY_REWRITE.value: rewrite,
        }

    async def execute(
        self, job: AnalysisJobSnapshot, monitor: AnalysisLeaseMonitor
    ) -> AnalysisExecutionOutput:
        executor = self._executors.get(job.result_contract)
        if executor is None:
            raise AnalysisExecutionError("analysis_cli_unsupported")
        return await executor.execute(job, monitor)
