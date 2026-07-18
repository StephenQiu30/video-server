"""Typed PostgreSQL boundary for atomic source-resolution creation."""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Engine

from video_server.errors import DomainError
from video_server.job.idempotency import ResolutionRequest
from video_server.job.state import JobStage, JobStatus
from video_server.security.envelope import EnvelopeCipher

Clock = Callable[[], datetime]
OpaqueIdFactory = Callable[[str], str]

_SAFE_OWNER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_SAFE_IDS = {
    "job": re.compile(r"^job_[A-Za-z0-9_-]{1,124}$"),
    "res": re.compile(r"^res_[A-Za-z0-9_-]{1,124}$"),
}


class CreateDisposition(StrEnum):
    CREATED = "created"
    REPLAYED = "replayed"


@dataclass(frozen=True, slots=True)
class CreateResolutionCommand:
    owner_id: str
    idempotency_key: str = field(repr=False)
    request: ResolutionRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.owner_id, str) or _SAFE_OWNER.fullmatch(self.owner_id) is None:
            raise ValueError("owner_id must use the stable safe identifier alphabet")
        if not isinstance(self.idempotency_key, str):
            raise TypeError("idempotency_key must be a string")
        if not isinstance(self.request, ResolutionRequest):
            raise TypeError("request must be a ResolutionRequest")


@dataclass(frozen=True, slots=True)
class CreateResolutionResult:
    disposition: CreateDisposition
    resolution_id: str
    job_id: str
    status: JobStatus
    stage: JobStage
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CreateDisposition):
            raise TypeError("disposition must be a CreateDisposition")
        _validate_id(self.resolution_id, kind="res")
        _validate_id(self.job_id, kind="job")
        if self.status is not JobStatus.QUEUED or self.stage is not JobStage.VALIDATING_URL:
            raise ValueError("create result must preserve the original queued snapshot")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must include timezone information")


class ResolutionCreatePersistenceError(DomainError):
    """A safe source-resolution create failure."""


class PostgresResolutionCreateStore:
    """Create or replay a source-resolution aggregate in one transaction."""

    __slots__ = ("_cipher", "_clock", "_engine", "_hmac_key", "_id_factory")

    def __init__(
        self,
        engine: Engine,
        cipher: EnvelopeCipher,
        *,
        hmac_key: bytes,
        clock: Clock | None = None,
        id_factory: OpaqueIdFactory | None = None,
    ) -> None:
        if not isinstance(engine, Engine):
            raise TypeError("engine must be a SQLAlchemy Engine")
        if not isinstance(cipher, EnvelopeCipher):
            raise TypeError("cipher must be an EnvelopeCipher")
        if type(hmac_key) is not bytes or len(hmac_key) != 32:
            raise ValueError("hmac_key must contain exactly 32 bytes")
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        if id_factory is not None and not callable(id_factory):
            raise TypeError("id_factory must be callable")
        self._engine = engine
        self._cipher = cipher
        self._hmac_key = hmac_key
        self._clock = clock or _utc_now
        self._id_factory = id_factory or _new_id

    def create(self, command: CreateResolutionCommand) -> CreateResolutionResult:
        if not isinstance(command, CreateResolutionCommand):
            raise TypeError("command must be a CreateResolutionCommand")
        raise NotImplementedError


def _validate_id(value: object, *, kind: str) -> str:
    if not isinstance(value, str) or _SAFE_IDS[kind].fullmatch(value) is None:
        raise ValueError(f"{kind} id must use the stable safe identifier alphabet")
    return value


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_id(kind: str) -> str:
    return _validate_id(f"{kind}_{secrets.token_urlsafe(18)}", kind=kind)
