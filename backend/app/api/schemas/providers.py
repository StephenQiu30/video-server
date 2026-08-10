from __future__ import annotations

from datetime import datetime

from app.api.schemas.common import StrictModel
from app.application.providers import ProviderStatusView
from app.domain.providers import (
    ProviderAccessMode,
    ProviderCapability,
    ProviderSupportStatus,
)


class ProviderStatusResponse(StrictModel):
    key: str
    display_name: str
    registered: bool
    extractor_exists: bool
    capabilities: tuple[ProviderCapability, ...]
    access_modes: tuple[ProviderAccessMode, ...]
    status: ProviderSupportStatus
    last_verified_at: datetime | None
    user_action: str | None

    @classmethod
    def from_view(cls, value: ProviderStatusView) -> ProviderStatusResponse:
        return cls(
            key=value.key,
            display_name=value.display_name,
            registered=value.registered,
            extractor_exists=value.extractor_exists,
            capabilities=value.capabilities,
            access_modes=value.access_modes,
            status=value.status,
            last_verified_at=value.last_verified_at,
            user_action=value.user_action,
        )


class ProviderListResponse(StrictModel):
    items: tuple[ProviderStatusResponse, ...]

    @classmethod
    def from_views(cls, values: tuple[ProviderStatusView, ...]) -> ProviderListResponse:
        return cls(
            items=tuple(ProviderStatusResponse.from_view(item) for item in values)
        )
