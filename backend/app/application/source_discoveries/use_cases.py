from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from app.application.downloads import (
    ApplicationError,
    ApplicationErrorCode,
    DownloadRepository,
    InspectionCreate,
    InspectionView,
    PersistenceIdempotencyConflict,
    RequestFingerprinter,
    UrlCipher,
)
from app.application.downloads.validation import (
    validate_idempotency_key,
    validate_now,
    validate_owner_hash,
)
from app.application.downloads.views import inspection_view
from app.application.source_discoveries.models import (
    SourceDiscoveryCreate,
    SourceDiscoveryItemCreate,
    SourceDiscoveryItemSnapshot,
    SourceDiscoveryItemView,
    SourceDiscoverySnapshot,
    SourceDiscoveryView,
)
from app.application.source_discoveries.ports import (
    ArticleAccessRestricted,
    ArticleDiscoveryAdapter,
    ArticleDiscoveryFailure,
    SourceDiscoveryIdempotencyConflict,
    SourceDiscoveryRepository,
)
from app.application.source_discoveries.url_admission import canonicalize_article_url
from app.domain.downloads import (
    AccessDecision,
    EntitlementState,
    ExecutionMode,
    IdentityState,
    ProtectionState,
    SourceOrigin,
)
from app.domain.identifiers import SourceDiscoveryAdapter
from app.domain.providers import ProviderKey
from app.domain.source_discovery import (
    DiscoveryItemKind,
    DiscoveryItemStatus,
    DiscoveryStatus,
)

ADAPTER_VERSION = SourceDiscoveryAdapter.WECHAT_ARTICLE
PROVIDER_KEY = ProviderKey.WECHAT_OFFICIAL_ACCOUNT_ARTICLE


class CreateSourceDiscovery:
    def __init__(
        self,
        repository: SourceDiscoveryRepository,
        adapter: ArticleDiscoveryAdapter,
        url_cipher: UrlCipher,
        fingerprinter: RequestFingerprinter,
        *,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
        ttl: timedelta,
        max_items: int,
    ) -> None:
        if ttl <= timedelta(0) or max_items < 1:
            raise ValueError("source discovery limits must be positive")
        self._repository = repository
        self._adapter = adapter
        self._url_cipher = url_cipher
        self._fingerprinter = fingerprinter
        self._now = now
        self._new_id = new_id
        self._ttl = ttl
        self._max_items = max_items

    async def __call__(
        self, url: str, owner_hash: str, idempotency_key: str
    ) -> SourceDiscoveryView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        try:
            canonical_url = canonicalize_article_url(url)
        except ValueError as exc:
            raise ApplicationError(ApplicationErrorCode.INVALID_URL) from exc
        request_fingerprint = self._fingerprinter.fingerprint(
            "source-discovery", canonical_url
        )
        existing = await self._repository.find_by_idempotency(
            owner_hash, idempotency_key
        )
        if existing is not None:
            if existing.request_fingerprint != request_fingerprint:
                raise ApplicationError(ApplicationErrorCode.IDEMPOTENCY_CONFLICT)
            return source_discovery_view(existing)
        try:
            result = await self._adapter.discover(canonical_url)
        except ArticleAccessRestricted as exc:
            raise ApplicationError(
                ApplicationErrorCode.ARTICLE_ACCESS_RESTRICTED
            ) from exc
        except ArticleDiscoveryFailure as exc:
            raise ApplicationError(
                ApplicationErrorCode.ARTICLE_DISCOVERY_FAILED
            ) from exc
        if len(result.items) > self._max_items:
            raise ApplicationError(ApplicationErrorCode.ARTICLE_DISCOVERY_FAILED)
        now = validate_now(self._now())
        command = SourceDiscoveryCreate(
            id=self._new_id(),
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            encrypted_url=self._url_cipher.encrypt(canonical_url),
            source_fingerprint=self._fingerprinter.fingerprint(
                "article-source", canonical_url
            ),
            provider_key=PROVIDER_KEY,
            title=_clean_title(result.title, "微信公众号文章"),
            adapter_version=ADAPTER_VERSION,
            status=DiscoveryStatus.READY if result.items else DiscoveryStatus.EMPTY,
            expires_at=now + self._ttl,
            items=tuple(
                SourceDiscoveryItemCreate(
                    id=self._new_id(),
                    item_ref=self._new_id(),
                    position=position,
                    kind=item.kind,
                    child_provider=item.child_provider,
                    title=_clean_title(item.title, f"文章视频 {position + 1}"),
                    duration_ms=item.duration_ms,
                    identity_evidence_hash=item.identity_evidence_hash,
                    decision_hint=item.decision_hint,
                    status=item.status,
                )
                for position, item in enumerate(result.items)
            ),
        )
        try:
            saved = await self._repository.save(command)
        except SourceDiscoveryIdempotencyConflict as exc:
            raise ApplicationError(ApplicationErrorCode.IDEMPOTENCY_CONFLICT) from exc
        return source_discovery_view(saved.discovery)


class GetSourceDiscovery:
    def __init__(
        self, repository: SourceDiscoveryRepository, *, now: Callable[[], datetime]
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(
        self, discovery_id: UUID, owner_hash: str
    ) -> SourceDiscoveryView:
        snapshot = await self._repository.get(
            discovery_id, validate_owner_hash(owner_hash), validate_now(self._now())
        )
        if snapshot is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        return source_discovery_view(snapshot)


class InspectDiscoveredItem:
    def __init__(
        self,
        discoveries: SourceDiscoveryRepository,
        downloads: DownloadRepository,
        fingerprinter: RequestFingerprinter,
        *,
        now: Callable[[], datetime],
        new_id: Callable[[], UUID],
        inspection_ttl: timedelta,
    ) -> None:
        self._discoveries = discoveries
        self._downloads = downloads
        self._fingerprinter = fingerprinter
        self._now = now
        self._new_id = new_id
        self._inspection_ttl = inspection_ttl

    async def __call__(
        self,
        discovery_id: UUID,
        item_ref: UUID,
        owner_hash: str,
        idempotency_key: str,
    ) -> InspectionView:
        owner_hash = validate_owner_hash(owner_hash)
        idempotency_key = validate_idempotency_key(idempotency_key)
        now = validate_now(self._now())
        selected = await self._discoveries.select_item(
            discovery_id, item_ref, owner_hash, now
        )
        if selected is None:
            raise ApplicationError(ApplicationErrorCode.NOT_FOUND)
        decision = _item_decision(selected.item)
        command = InspectionCreate(
            id=self._new_id(),
            owner_hash=owner_hash,
            idempotency_key=idempotency_key,
            request_fingerprint=self._fingerprinter.fingerprint(
                "inspection-discovered", str(discovery_id), str(item_ref)
            ),
            url_ciphertext=selected.discovery.encrypted_url.ciphertext,
            url_nonce=selected.discovery.encrypted_url.nonce,
            url_key_id=selected.discovery.encrypted_url.key_id,
            extractor_key=decision[0],
            provider_media_id=f"discovered-{item_ref}",
            title=selected.item.title,
            duration_seconds=(selected.item.duration_ms or 0) // 1000,
            metadata={
                "source_origin": SourceOrigin.PUBLIC_URL.value,
                "execution_mode": decision[1].value,
                "access_decision": decision[2].value,
                "entitlement_state": EntitlementState.UNKNOWN.value,
                "identity_state": decision[3].value,
                "protection_state": ProtectionState.UNKNOWN.value,
                "rights_basis": None,
                "restriction_reason": decision[4],
                "user_action": decision[5],
                "source_discovery_id": str(discovery_id),
                "source_discovery_item_ref": str(item_ref),
            },
            expires_at=min(now + self._inspection_ttl, selected.discovery.expires_at),
            formats=(),
        )
        try:
            saved = await self._downloads.save_inspection(command)
        except PersistenceIdempotencyConflict as exc:
            raise ApplicationError(ApplicationErrorCode.IDEMPOTENCY_CONFLICT) from exc
        return inspection_view(saved.inspection)


def source_discovery_view(snapshot: SourceDiscoverySnapshot) -> SourceDiscoveryView:
    return SourceDiscoveryView(
        id=snapshot.id,
        provider_key=snapshot.provider_key,
        title=snapshot.title,
        status=snapshot.status,
        expires_at=snapshot.expires_at,
        items=tuple(
            SourceDiscoveryItemView(
                item_ref=item.item_ref,
                kind=item.kind,
                title=item.title,
                duration_ms=item.duration_ms,
                decision_hint=item.decision_hint,
                status=item.status,
            )
            for item in snapshot.items
        ),
    )


def _item_decision(
    item: SourceDiscoveryItemSnapshot,
) -> tuple[str, ExecutionMode, AccessDecision, IdentityState, str, str]:
    if item.kind is DiscoveryItemKind.TENCENT_VIDEO:
        return (
            ProviderKey.QQVIDEO,
            ExecutionMode.PROVIDER_RUNNER,
            AccessDecision.PLAYBACK_ONLY,
            IdentityState.VERIFIED,
            "tencent_consumer_download_disabled",
            "请在腾讯视频官方客户端播放；VIP/付费内容不提供下载。",
        )
    if item.kind is DiscoveryItemKind.WECHAT_CHANNELS:
        return (
            ProviderKey.WECHAT_CHANNELS,
            ExecutionMode.VERIFIED_IMPORT,
            AccessDecision.EXPORT_REQUIRED,
            IdentityState.VERIFIED,
            "wechat_channels_export_required",
            "请在微信中合法导出自有明文 MP4 后通过本地导入上传。",
        )
    if item.kind is DiscoveryItemKind.OFFICIAL_ACCOUNT_NATIVE:
        verified = item.status is DiscoveryItemStatus.READY
        return (
            PROVIDER_KEY,
            ExecutionMode.ARTICLE_NATIVE,
            AccessDecision.BLOCKED,
            IdentityState.VERIFIED if verified else IdentityState.AMBIGUOUS,
            (
                "article_native_download_not_enabled"
                if verified
                else "article_video_identity_unverified"
            ),
            "已发现公众号原生视频；安全下载执行器完成授权验收前暂不提供下载。",
        )
    return (
        PROVIDER_KEY,
        ExecutionMode.ARTICLE_NATIVE,
        AccessDecision.UNSUPPORTED,
        IdentityState.UNKNOWN,
        "unsupported_article_embed",
        "文章中的该嵌入类型暂不支持下载。",
    )


def _clean_title(value: str, fallback: str) -> str:
    normalized = " ".join(value.split()).strip()
    return (normalized or fallback)[:200]
