from __future__ import annotations

from typing import Protocol

from app.services.analysis.models import AnalysisJobSnapshot
from app.services.analysis.rules.enums import AnalysisResultContract
from app.services.analysis_execution.errors import AnalysisExecutionError
from app.services.analysis_execution.models import AnalysisExecutionOutput
from app.services.analysis_execution.monitor import AnalysisLeaseMonitor


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
