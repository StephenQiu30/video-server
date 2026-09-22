from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from app.schemas.common import StrictModel
from app.services.provider_access import ProviderAccessPolicy
from app.services.provider_types import (
    ProviderAccessMode,
    ProviderAccessState,
    ProviderAuthorizationAction,
    ProviderAuthorizationSource,
    ProviderCapability,
    ProviderSupportStatus,
    provider_authorization_action,
)
from app.services.providers import ProviderEvidenceState, ProviderStatusView


class ProviderAccessPolicyResponse(StrictModel):
    id: ProviderAccessPolicy
    configured: bool


class ProviderStatusResponse(StrictModel):
    key: str
    display_name: str
    registered: bool
    extractor_exists: bool
    capabilities: tuple[ProviderCapability, ...]
    access_modes: tuple[ProviderAccessMode, ...]
    access_state: ProviderAccessState
    status: ProviderSupportStatus
    last_checked_at: datetime | None
    last_check_succeeded: bool | None
    download_supported: bool
    download_available: bool
    last_media_verified_at: datetime | None
    last_verified_at: datetime | None
    user_action: str | None
    access_policies: tuple[ProviderAccessPolicyResponse, ...]
    default_access_policy_id: ProviderAccessPolicy | None
    evidence_state: ProviderEvidenceState
    hosts: tuple[str, ...]
    host_suffixes: tuple[str, ...]
    route_retry_at: datetime | None = None
    authorization_action: ProviderAuthorizationAction

    @classmethod
    def from_view(
        cls,
        value: ProviderStatusView,
        *,
        browser_session_allowed: bool = False,
    ) -> ProviderStatusResponse:
        return cls(
            key=value.key,
            display_name=value.display_name,
            registered=value.registered,
            extractor_exists=value.extractor_exists,
            capabilities=value.capabilities,
            access_modes=value.access_modes,
            access_state=value.access_state,
            status=value.status,
            last_checked_at=value.last_checked_at,
            last_check_succeeded=value.last_check_succeeded,
            download_supported=value.download_supported,
            download_available=value.download_available,
            last_media_verified_at=value.last_media_verified_at,
            last_verified_at=value.last_verified_at,
            user_action=value.user_action,
            access_policies=tuple(
                ProviderAccessPolicyResponse(id=item.id, configured=item.configured)
                for item in value.access_policies
            ),
            default_access_policy_id=value.default_access_policy_id,
            evidence_state=value.evidence_state,
            hosts=value.hosts,
            host_suffixes=value.host_suffixes,
            route_retry_at=value.route_retry_at,
            authorization_action=provider_authorization_action(
                value.key,
                access_modes=value.access_modes,
                status=value.status,
                last_check_succeeded=value.last_check_succeeded,
                browser_session_allowed=browser_session_allowed,
            ),
        )


class ProviderListResponse(StrictModel):
    items: tuple[ProviderStatusResponse, ...]

    @classmethod
    def from_views(
        cls,
        values: tuple[ProviderStatusView, ...],
        *,
        browser_session_allowed: bool = False,
    ) -> ProviderListResponse:
        return cls(
            items=tuple(
                ProviderStatusResponse.from_view(
                    item,
                    browser_session_allowed=browser_session_allowed,
                )
                for item in values
            )
        )


class ProviderAuthorizationStatus(StrEnum):
    PENDING = "pending"
    SOURCE_AVAILABLE = "source_available"
    AUTHORIZATION_REQUIRED = "authorization_required"
    PERMISSION_REQUIRED = "permission_required"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BeginProviderAuthorizationRequest(StrictModel):
    """Select the explicit local browser session used for authorization."""

    source: ProviderAuthorizationSource = ProviderAuthorizationSource.CURRENT_CHROME


class ProviderAuthorizationResponse(StrictModel):
    transaction_id: str
    provider_key: str
    status: ProviderAuthorizationStatus
    expires_at: datetime
