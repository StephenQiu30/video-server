from app.domain.imports import ImportErrorCode


class ImportLeaseLost(RuntimeError):
    pass


class ImportExecutionUnavailable(RuntimeError):
    pass


class ImportVerificationRejected(ValueError):
    def __init__(self, code: ImportErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
