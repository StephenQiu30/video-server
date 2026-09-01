from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.application.downloads import EncryptedUrl
from app.application.source_discoveries import (
    SourceDiscoveryCreate,
    SourceDiscoveryIdempotencyConflict,
    SourceDiscoveryItemCreate,
)
from app.domain.source_discovery import (
    DiscoveryDecisionHint,
    DiscoveryItemKind,
    DiscoveryItemStatus,
    DiscoveryStatus,
)
from app.infrastructure.database.source_discovery_repository import (
    SqlAlchemySourceDiscoveryRepository,
)
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

NOW = datetime(2026, 8, 27, tzinfo=UTC)


def command(
    *, owner: str = "a" * 64, fingerprint: str = "f" * 64
) -> SourceDiscoveryCreate:
    return SourceDiscoveryCreate(
        id=uuid4(),
        owner_hash=owner,
        idempotency_key="discovery-1",
        request_fingerprint=fingerprint,
        encrypted_url=EncryptedUrl(b"cipher", b"nonce", "fernet"),
        source_fingerprint="s" * 64,
        provider_key="wechat_official_account_article",
        title="Article",
        adapter_version="wechat-article-static",
        status=DiscoveryStatus.READY,
        expires_at=NOW + timedelta(minutes=15),
        items=(
            SourceDiscoveryItemCreate(
                id=uuid4(),
                item_ref=uuid4(),
                position=0,
                kind=DiscoveryItemKind.WECHAT_CHANNELS,
                child_provider="wechat_channels",
                title="Channels item",
                duration_ms=None,
                identity_evidence_hash="i" * 64,
                decision_hint=DiscoveryDecisionHint.EXPORT_REQUIRED,
                status=DiscoveryItemStatus.READY,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_repository_enforces_owner_ttl_item_ref_and_idempotency(
    postgres_engine: AsyncEngine,
) -> None:
    repository = SqlAlchemySourceDiscoveryRepository(
        async_sessionmaker(postgres_engine, expire_on_commit=False)
    )
    create = command()

    first = await repository.save(create)
    replay = await repository.save(create)

    assert first.created is True
    assert replay.created is False
    found = await repository.find_by_idempotency(
        create.owner_hash, create.idempotency_key
    )
    assert found is not None
    assert found.request_fingerprint == create.request_fingerprint
    assert await repository.get(create.id, "b" * 64, NOW) is None
    assert await repository.get(create.id, create.owner_hash, create.expires_at) is None
    selected = await repository.select_item(
        create.id, create.items[0].item_ref, create.owner_hash, NOW
    )
    assert selected is not None
    assert selected.item.kind is DiscoveryItemKind.WECHAT_CHANNELS
    assert (
        await repository.select_item(create.id, uuid4(), create.owner_hash, NOW) is None
    )

    with pytest.raises(SourceDiscoveryIdempotencyConflict):
        await repository.save(command(fingerprint="x" * 64))
