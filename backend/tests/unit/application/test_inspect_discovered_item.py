from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.application.downloads import (
    EncryptedUrl,
    InspectionSaveResult,
    InspectionSnapshot,
)
from app.application.downloads.fingerprints import HmacRequestFingerprinter
from app.application.source_discoveries import (
    InspectDiscoveredItem,
    SourceDiscoveryItemSelection,
    SourceDiscoveryItemSnapshot,
    SourceDiscoverySnapshot,
)
from app.domain.downloads import AccessDecision, IdentityState
from app.domain.source_discovery import (
    DiscoveryDecisionHint,
    DiscoveryItemKind,
    DiscoveryItemStatus,
    DiscoveryStatus,
)

NOW = datetime(2026, 8, 27, tzinfo=UTC)
DISCOVERY_ID = UUID("44444444-4444-4444-8444-444444444444")
ITEM_REF = UUID("55555555-5555-4555-8555-555555555555")


class Discoveries:
    def __init__(self, item: SourceDiscoveryItemSnapshot | None) -> None:
        self.item = item

    async def select_item(
        self,
        discovery_id: UUID,
        item_ref: UUID,
        owner_hash: str,
        now: datetime,
    ) -> SourceDiscoveryItemSelection | None:
        if self.item is None:
            return None
        return SourceDiscoveryItemSelection(
            discovery=SourceDiscoverySnapshot(
                id=discovery_id,
                owner_hash=owner_hash,
                request_fingerprint="f" * 64,
                encrypted_url=EncryptedUrl(b"cipher", b"nonce", "fernet-v1"),
                source_fingerprint="s" * 64,
                provider_key="wechat_official_account_article",
                title="Article",
                adapter_version="wechat-article-static-v1",
                status=DiscoveryStatus.READY,
                expires_at=NOW + timedelta(minutes=10),
                created_at=NOW,
                items=(self.item,),
            ),
            item=self.item,
        )


class Downloads:
    def __init__(self) -> None:
        self.commands: list[object] = []

    async def save_inspection(self, command: object) -> InspectionSaveResult:
        from app.application.downloads import InspectionCreate

        assert isinstance(command, InspectionCreate)
        self.commands.append(command)
        return InspectionSaveResult(
            inspection=InspectionSnapshot(
                id=command.id,
                owner_hash=command.owner_hash,
                request_fingerprint=command.request_fingerprint,
                extractor_key=command.extractor_key,
                provider_media_id=command.provider_media_id,
                title=command.title,
                duration_seconds=command.duration_seconds,
                metadata=command.metadata,
                expires_at=command.expires_at,
                formats=(),
            ),
            created=True,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "status", "provider", "decision", "identity"),
    [
        (
            DiscoveryItemKind.TENCENT_VIDEO,
            DiscoveryItemStatus.READY,
            "qqvideo",
            AccessDecision.PLAYBACK_ONLY,
            IdentityState.VERIFIED,
        ),
        (
            DiscoveryItemKind.WECHAT_CHANNELS,
            DiscoveryItemStatus.READY,
            "wechat_channels",
            AccessDecision.EXPORT_REQUIRED,
            IdentityState.VERIFIED,
        ),
        (
            DiscoveryItemKind.OFFICIAL_ACCOUNT_NATIVE,
            DiscoveryItemStatus.READY,
            "wechat_official_account_article",
            AccessDecision.BLOCKED,
            IdentityState.VERIFIED,
        ),
        (
            DiscoveryItemKind.OFFICIAL_ACCOUNT_NATIVE,
            DiscoveryItemStatus.IDENTITY_UNVERIFIED,
            "wechat_official_account_article",
            AccessDecision.BLOCKED,
            IdentityState.AMBIGUOUS,
        ),
        (
            DiscoveryItemKind.UNKNOWN,
            DiscoveryItemStatus.IDENTITY_UNVERIFIED,
            "wechat_official_account_article",
            AccessDecision.UNSUPPORTED,
            IdentityState.UNKNOWN,
        ),
    ],
)
async def test_selection_creates_only_restricted_owner_scoped_inspections(
    kind: DiscoveryItemKind,
    status: DiscoveryItemStatus,
    provider: str,
    decision: AccessDecision,
    identity: IdentityState,
) -> None:
    item = SourceDiscoveryItemSnapshot(
        item_ref=ITEM_REF,
        position=0,
        kind=kind,
        child_provider=provider,
        title="Selected item",
        duration_ms=None,
        identity_evidence_hash="i" * 64,
        decision_hint=DiscoveryDecisionHint.UNSUPPORTED,
        status=status,
    )
    downloads = Downloads()
    use_case = InspectDiscoveredItem(
        Discoveries(item),  # type: ignore[arg-type]
        downloads,  # type: ignore[arg-type]
        HmacRequestFingerprinter(b"fingerprint-secret"),
        now=lambda: NOW,
        new_id=uuid4,
        inspection_ttl=timedelta(minutes=15),
    )

    view = await use_case(DISCOVERY_ID, ITEM_REF, "a" * 64, "inspect-item-1")

    assert view.extractor_key == provider
    assert view.access_decision is decision
    assert view.identity_state is identity
    assert view.formats == ()
    command = downloads.commands[0]
    assert not {"url", "iframe_url", "cdn_url", "raw_html", "ticket"} & set(
        command.metadata
    )
    assert command.url_ciphertext == b"cipher"
    assert command.expires_at == NOW + timedelta(minutes=10)
