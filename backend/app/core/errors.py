"""Stable application errors safe for API clients."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.error_codes import ErrorCode


@dataclass(slots=True)
class AppError(Exception):
    status: int
    code: ErrorCode | str
    title: str
    detail: str
    headers: dict[str, str] | None = None

    def __post_init__(self) -> None:
        self.code = ErrorCode(self.code)
        Exception.__init__(self, self.detail)
