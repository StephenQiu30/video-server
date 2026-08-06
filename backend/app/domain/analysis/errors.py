from __future__ import annotations

from app.domain.analysis.enums import AnalysisValidationCode


class InvalidAnalysisTransition(ValueError):
    """A command violates the independent analysis job state contract."""


class AnalysisValidationError(ValueError):
    def __init__(self, code: AnalysisValidationCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")
