"""Scoped identity fixtures for resolution-create writer tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from sqlalchemy import Engine

from tests.integration.persistence._resolution_aggregate import NOW
from tests.integration.persistence._resolution_create_store import HMAC_KEY, KEK, MutableClock
from video_server.job.idempotency import ResolutionRequest
from video_server.persistence.resolution_create import (
    CreateResolutionCommand,
    PostgresResolutionCreateStore,
)
from video_server.security.envelope import EnvelopeCipher

OWNER_A = "owner_scope_a"
OWNER_B = "owner_scope_b"
KEY_A = "resolve-scope-key-0001"
KEY_B = "resolve-scope-key-0002"
URL_A = "https://media.example/video-a"
URL_B = "https://media.example/video-b"


@dataclass(slots=True)
class SequentialIdFactory:
    _counts: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def __call__(self, kind: str) -> str:
        with self._lock:
            count = self._counts.get(kind, 0) + 1
            self._counts[kind] = count
        return f"{kind}_scope_{count:04d}"


def scoped_request(*, url: str = URL_A) -> ResolutionRequest:
    return ResolutionRequest(
        url=url,
        rights_confirmed=True,
        rights_statement_version="rights-2026-07-18.1",
        rights_statement_locale="zh-CN",
    )


def scoped_command(
    *,
    owner_id: str = OWNER_A,
    key: str = KEY_A,
    request: ResolutionRequest | None = None,
) -> CreateResolutionCommand:
    return CreateResolutionCommand(
        owner_id=owner_id,
        idempotency_key=key,
        request=request or scoped_request(),
    )


def scoped_store(
    engine: Engine,
    *,
    factory: SequentialIdFactory | None = None,
    clock: MutableClock | None = None,
) -> PostgresResolutionCreateStore:
    return PostgresResolutionCreateStore(
        engine,
        EnvelopeCipher({"kek-1": KEK}, current_key_id="kek-1"),
        hmac_key=HMAC_KEY,
        id_factory=factory or SequentialIdFactory(),
        clock=clock or MutableClock(NOW),
    )
