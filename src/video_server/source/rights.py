"""Versioned rights-statement catalog boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RightsStatement:
    version: str
    locale: str
    statement: str
    statement_sha256: str
    effective_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class RightsAttestation:
    version: str
    locale: str
    statement_sha256: str
    confirmed_at: datetime


class RightsCatalog:
    """Immutable catalog facade; implementation validates hashes and lifecycle."""

    @classmethod
    def load(cls, path: str | Path) -> RightsCatalog:
        raise NotImplementedError("rights catalog loading is not implemented")

    def current(self, locale: str | None, *, now: datetime) -> RightsStatement:
        raise NotImplementedError("rights current lookup is not implemented")

    def attest(
        self,
        *,
        confirmed: bool,
        version: str,
        locale: str,
        now: datetime,
    ) -> RightsAttestation:
        raise NotImplementedError("rights attestation is not implemented")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RightsCatalog:
        raise NotImplementedError("rights catalog parsing is not implemented")
