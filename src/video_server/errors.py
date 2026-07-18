"""Stable domain errors shared by HTTP and worker adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class DomainError(Exception):
    """A safe, canonical failure that may cross an application boundary."""

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        retryable: bool = False,
        field: str | None = None,
        actions: Sequence[str] | None = None,
        policy: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.retryable = retryable
        self.field = field
        self.actions = tuple(actions) if actions is not None else None
        self.policy = dict(policy) if policy is not None else None
