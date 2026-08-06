"""Stable application errors safe for API clients."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppError(Exception):
    status: int
    code: str
    title: str
    detail: str

    def __post_init__(self) -> None:
        Exception.__init__(self, self.detail)
