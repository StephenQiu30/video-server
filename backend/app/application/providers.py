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
    profile_version: str | None
    registered: bool
    extractor_exists: bool
    capabilities: tuple[ProviderCapability, ...]
    access_modes: tuple[ProviderAccessMode, ...]
    status: ProviderSupportStatus
    last_checked_at: datetime | None
    last_check_succeeded: bool | None
    download_available: bool
    last_media_verified_at: datetime | None
    last_verified_at: datetime | None
    user_action: str | None

    @property
    def download_supported(self) -> bool:
        downloadable = {
            ProviderCapability.SINGLE_VIDEO,
            ProviderCapability.SHORT_VIDEO,
            ProviderCapability.CLIP_OR_VOD,
        }
        return (
            self.registered
            and self.extractor_exists
            and self.status
            not in {
                ProviderSupportStatus.DISABLED,
                ProviderSupportStatus.UNSUPPORTED,
            }
            and bool(downloadable.intersection(self.capabilities))
        )
