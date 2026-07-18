"""Typed PostgreSQL boundary for atomic source-resolution creation."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from video_server.job.idempotency import (
    ResolutionRequest,
    digest_idempotency_key,
    digest_resolution_request,
)
from video_server.job.state import JobStage, JobStatus
from video_server.persistence._resolution_create_errors import (
    ResolutionCreatePersistenceError,
    internal_create_error,
    rejected_create,
)
from video_server.persistence._resolution_create_ids import (
    new_resolution_id,
    validate_resolution_id,
)
from video_server.persistence._resolution_create_writer import (
    CreateRejectedSignal,
    PreparedResolutionCreate,
    UnsafeTransactionSignal,
    create_resolution,
)
from video_server.security.envelope import EnvelopeCipher
from video_server.source.urls import canonicalize_source_url

Clock = Callable[[], datetime]
OpaqueIdFactory = Callable[[str], str]

__all__ = [
    "CreateDisposition",
    "CreateResolutionCommand",
    "CreateResolutionResult",
    "PostgresResolutionCreateStore",
    "ResolutionCreatePersistenceError",
]

_SAFE_OWNER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_RETRYABLE_TRANSACTION_STATES = frozenset({"40001", "40P01"})
_MAX_TRANSACTION_ATTEMPTS = 3


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
        validate_resolution_id(self.resolution_id, kind="res")
        validate_resolution_id(self.job_id, kind="job")
        if self.status is not JobStatus.QUEUED or self.stage is not JobStage.VALIDATING_URL:
            raise ValueError("create result must preserve the original queued snapshot")
        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must include timezone information")


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
        self._id_factory = id_factory or new_resolution_id

    def create(self, command: CreateResolutionCommand) -> CreateResolutionResult:
        if not isinstance(command, CreateResolutionCommand):
            raise TypeError("command must be a CreateResolutionCommand")
        prepared = self._prepare(command)
        for attempt in range(_MAX_TRANSACTION_ATTEMPTS):
            try:
                with self._engine.begin() as connection:
                    persisted = create_resolution(
                        connection,
                        prepared,
                        cipher=self._cipher,
                        clock=self._clock,
                        id_factory=self._validated_new_id,
                    )
                return CreateResolutionResult(
                    CreateDisposition.REPLAYED if persisted.replayed else CreateDisposition.CREATED,
                    persisted.resolution_id,
                    persisted.job_id,
                    JobStatus.QUEUED,
                    JobStage.VALIDATING_URL,
                    persisted.created_at,
                )
            except CreateRejectedSignal as error:
                raise rejected_create(error.code) from None
            except UnsafeTransactionSignal:
                raise internal_create_error() from None
            except DBAPIError as error:
                sqlstate = getattr(error.orig, "sqlstate", None)
                can_retry = (
                    sqlstate in _RETRYABLE_TRANSACTION_STATES
                    and attempt + 1 < _MAX_TRANSACTION_ATTEMPTS
                )
                if can_retry:
                    continue
                raise internal_create_error() from None
            except SQLAlchemyError:
                raise internal_create_error() from None
            except (TypeError, ValueError):
                raise internal_create_error() from None
            except Exception:
                raise internal_create_error() from None
        raise AssertionError("transaction retry loop exhausted")

    def _prepare(self, command: CreateResolutionCommand) -> PreparedResolutionCreate:
        try:
            key_digest = digest_idempotency_key(
                command.idempotency_key,
                hmac_key=self._hmac_key,
            )
        except ValueError:
            raise rejected_create("IDEMPOTENCY_KEY_INVALID") from None
        request = command.request
        return PreparedResolutionCreate(
            owner_id=command.owner_id,
            idempotency_key_digest=key_digest,
            request_digest=digest_resolution_request(request, hmac_key=self._hmac_key),
            canonical_url=canonicalize_source_url(request.url),
            rights_confirmed=request.rights_confirmed,
            rights_statement_version=request.rights_statement_version,
            rights_statement_locale=request.rights_statement_locale,
        )

    def _validated_new_id(self, kind: str) -> str:
        return validate_resolution_id(self._id_factory(kind), kind=kind)


def _utc_now() -> datetime:
    return datetime.now(UTC)
