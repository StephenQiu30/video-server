"""Public, non-secret Provider capability views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.providers import (
    ProviderAccessMode,
    ProviderCapability,
    ProviderSupportStatus,
)


@dataclass(frozen=True, slots=True)
class ProviderStatusView:
    key: str
    display_name: str
    registered: bool
    extractor_exists: bool
    capabilities: tuple[ProviderCapability, ...]
    access_modes: tuple[ProviderAccessMode, ...]
    status: ProviderSupportStatus
    last_media_verified_at: datetime | None
    last_verified_at: datetime | None
    user_action: str | None
