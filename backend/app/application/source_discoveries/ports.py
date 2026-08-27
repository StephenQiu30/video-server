from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.source_discoveries.models import (
    ArticleDiscoveryResult,
    SourceDiscoveryCreate,
    SourceDiscoveryItemSelection,
    SourceDiscoverySaveResult,
    SourceDiscoverySnapshot,
)


class ArticleDiscoveryAdapter(Protocol):
    async def discover(self, url: str) -> ArticleDiscoveryResult: ...


class SourceDiscoveryRepository(Protocol):
    async def save(
        self, command: SourceDiscoveryCreate
    ) -> SourceDiscoverySaveResult: ...

    async def get(
        self, discovery_id: UUID, owner_hash: str, now: datetime
    ) -> SourceDiscoverySnapshot | None: ...

    async def find_by_idempotency(
        self, owner_hash: str, idempotency_key: str
    ) -> SourceDiscoverySnapshot | None: ...

    async def select_item(
        self,
        discovery_id: UUID,
        item_ref: UUID,
        owner_hash: str,
        now: datetime,
    ) -> SourceDiscoveryItemSelection | None: ...


class ArticleDiscoveryFailure(RuntimeError):
    """The bounded article adapter could not produce a safe discovery."""


class ArticleAccessRestricted(ArticleDiscoveryFailure):
    """The article requires a challenge, authentication or entitlement."""


class SourceDiscoveryIdempotencyConflict(RuntimeError):
    """A discovery idempotency key was reused for a different article."""
