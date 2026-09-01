from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import StrictModel
from app.application.source_discoveries import SourceDiscoveryView
from app.domain.providers import ProviderKey
from app.domain.source_discovery import (
    DiscoveryDecisionHint,
    DiscoveryItemKind,
    DiscoveryItemStatus,
    DiscoveryStatus,
)


class SourceDiscoveryRequest(StrictModel):
    kind: Literal[ProviderKey.WECHAT_OFFICIAL_ACCOUNT_ARTICLE]
    url: str = Field(min_length=8, max_length=4096)


class SourceDiscoveryItemResponse(StrictModel):
    item_ref: UUID
    kind: DiscoveryItemKind
    title: str
    duration_ms: int | None
    decision_hint: DiscoveryDecisionHint
    status: DiscoveryItemStatus


class SourceDiscoveryResponse(StrictModel):
    id: UUID
    provider_key: str
    title: str
    status: DiscoveryStatus
    expires_at: datetime
    items: tuple[SourceDiscoveryItemResponse, ...]

    @classmethod
    def from_view(cls, view: SourceDiscoveryView) -> SourceDiscoveryResponse:
        return cls(
            id=view.id,
            provider_key=view.provider_key,
            title=view.title,
            status=view.status,
            expires_at=view.expires_at,
            items=tuple(
                SourceDiscoveryItemResponse(
                    item_ref=item.item_ref,
                    kind=item.kind,
                    title=item.title,
                    duration_ms=item.duration_ms,
                    decision_hint=item.decision_hint,
                    status=item.status,
                )
                for item in view.items
            ),
        )
