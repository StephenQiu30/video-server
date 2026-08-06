from __future__ import annotations


class RunnerFailure(RuntimeError):
    """Stable internal runner failure without provider or URL details."""

    def __init__(
        self,
        code: str,
        *,
        status: int = 422,
        message: str | None = None,
    ) -> None:
        self.code = code
        self.status = status
        self.message = message or code.replace("_", " ")
        super().__init__(self.message)
