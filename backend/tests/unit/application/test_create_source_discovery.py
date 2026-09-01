from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.application.downloads import (
    ApplicationError,
    ApplicationErrorCode,
    EncryptedUrl,
)
from app.application.downloads.fingerprints import HmacRequestFingerprinter
from app.application.source_discoveries import (
    CreateSourceDiscovery,
    SourceDiscoverySnapshot,
)
from app.domain.source_discovery import DiscoveryStatus

NOW = datetime(2026, 8, 27, tzinfo=UTC)
OWNER = "a" * 64
URL = "https://mp.weixin.qq.com/s/article_123"


class ExistingRepository:
    def __init__(self, snapshot: SourceDiscoverySnapshot) -> None:
        self.snapshot = snapshot

    async def find_by_idempotency(
        self, owner_hash: str, idempotency_key: str
    ) -> SourceDiscoverySnapshot | None:
        assert owner_hash == OWNER
        assert idempotency_key == "discovery-retry"
        return self.snapshot

    async def save(self, command: object) -> object:
        raise AssertionError("an idempotent replay must not write again")


class UnexpectedAdapter:
    async def discover(self, url: str) -> object:
        raise AssertionError("an idempotent replay must not refetch the article")


class UnexpectedCipher:
    def encrypt(self, value: str) -> EncryptedUrl:
        raise AssertionError("an idempotent replay must reuse encrypted state")


def existing_snapshot(request_fingerprint: str) -> SourceDiscoverySnapshot:
    return SourceDiscoverySnapshot(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        owner_hash=OWNER,
        request_fingerprint=request_fingerprint,
        encrypted_url=EncryptedUrl(b"cipher", b"nonce", "fernet"),
        source_fingerprint="s" * 64,
        provider_key="wechat_official_account_article",
        title="Article",
        adapter_version="wechat-article-static",
        status=DiscoveryStatus.EMPTY,
        expires_at=NOW + timedelta(minutes=10),
        created_at=NOW,
        items=(),
    )


def use_case(request_fingerprint: str) -> CreateSourceDiscovery:
    return CreateSourceDiscovery(
        ExistingRepository(existing_snapshot(request_fingerprint)),  # type: ignore[arg-type]
        UnexpectedAdapter(),  # type: ignore[arg-type]
        UnexpectedCipher(),
        HmacRequestFingerprinter(b"fingerprint-secret"),
        now=lambda: NOW,
        new_id=uuid4,
        ttl=timedelta(minutes=15),
        max_items=24,
    )


@pytest.mark.asyncio
async def test_idempotent_replay_does_not_refetch_article() -> None:
    fingerprinter = HmacRequestFingerprinter(b"fingerprint-secret")
    create = use_case(fingerprinter.fingerprint("source-discovery", URL))

    result = await create(URL, OWNER, "discovery-retry")

    assert result.id == UUID("11111111-1111-4111-8111-111111111111")


@pytest.mark.asyncio
async def test_idempotency_conflict_is_rejected_before_article_fetch() -> None:
    create = use_case("x" * 64)

    with pytest.raises(ApplicationError) as captured:
        await create(URL, OWNER, "discovery-retry")

    assert captured.value.code is ApplicationErrorCode.IDEMPOTENCY_CONFLICT
