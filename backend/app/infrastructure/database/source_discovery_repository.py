from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.downloads import EncryptedUrl
from app.application.source_discoveries import (
    SourceDiscoveryCreate,
    SourceDiscoveryIdempotencyConflict,
    SourceDiscoveryItemSelection,
    SourceDiscoveryItemSnapshot,
    SourceDiscoverySaveResult,
    SourceDiscoverySnapshot,
)
from app.domain.source_discovery import (
    DiscoveryDecisionHint,
    DiscoveryItemKind,
    DiscoveryItemStatus,
    DiscoveryStatus,
)

from .models import SourceDiscoveryItemRow, SourceDiscoveryRow


class SqlAlchemySourceDiscoveryRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, command: SourceDiscoveryCreate) -> SourceDiscoverySaveResult:
        async with self._sessions() as session:
            try:
                async with session.begin():
                    existing = await self._existing(session, command)
                    if existing is not None:
                        return SourceDiscoverySaveResult(
                            await self._snapshot(session, existing), created=False
                        )
                    row = SourceDiscoveryRow(
                        id=command.id,
                        owner_hash=command.owner_hash,
                        idempotency_key=command.idempotency_key,
                        request_fingerprint=command.request_fingerprint,
                        provider_key=command.provider_key,
                        url_ciphertext=command.encrypted_url.ciphertext,
                        url_nonce=command.encrypted_url.nonce,
                        url_key_id=command.encrypted_url.key_id,
                        source_fingerprint=command.source_fingerprint,
                        title=command.title,
                        adapter_version=command.adapter_version,
                        status=command.status.value,
                        expires_at=command.expires_at,
                    )
                    session.add(row)
                    await session.flush()
                    session.add_all(
                        [
                            SourceDiscoveryItemRow(
                                id=item.id,
                                discovery_id=command.id,
                                item_ref=item.item_ref,
                                position=item.position,
                                kind=item.kind.value,
                                child_provider=item.child_provider,
                                title=item.title,
                                duration_ms=item.duration_ms,
                                identity_evidence_hash=item.identity_evidence_hash,
                                decision_hint=item.decision_hint.value,
                                status=item.status.value,
                            )
                            for item in command.items
                        ]
                    )
                    await session.flush()
                    result = SourceDiscoverySaveResult(
                        await self._snapshot(session, row), created=True
                    )
                return result
            except IntegrityError:
                await session.rollback()
                existing = await self._existing(session, command)
                if existing is None:
                    raise
                return SourceDiscoverySaveResult(
                    await self._snapshot(session, existing), created=False
                )

    async def get(
        self, discovery_id: UUID, owner_hash: str, now: datetime
    ) -> SourceDiscoverySnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(SourceDiscoveryRow).where(
                    SourceDiscoveryRow.id == discovery_id,
                    SourceDiscoveryRow.owner_hash == owner_hash,
                    SourceDiscoveryRow.expires_at > now,
                )
            )
            return None if row is None else await self._snapshot(session, row)

    async def find_by_idempotency(
        self, owner_hash: str, idempotency_key: str
    ) -> SourceDiscoverySnapshot | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(SourceDiscoveryRow).where(
                    SourceDiscoveryRow.owner_hash == owner_hash,
                    SourceDiscoveryRow.idempotency_key == idempotency_key,
                )
            )
            return None if row is None else await self._snapshot(session, row)

    async def select_item(
        self,
        discovery_id: UUID,
        item_ref: UUID,
        owner_hash: str,
        now: datetime,
    ) -> SourceDiscoveryItemSelection | None:
        snapshot = await self.get(discovery_id, owner_hash, now)
        if snapshot is None:
            return None
        item = next(
            (item for item in snapshot.items if item.item_ref == item_ref), None
        )
        return (
            None
            if item is None
            else SourceDiscoveryItemSelection(discovery=snapshot, item=item)
        )

    @staticmethod
    async def _snapshot(
        session: AsyncSession, row: SourceDiscoveryRow
    ) -> SourceDiscoverySnapshot:
        items = tuple(
            (
                await session.scalars(
                    select(SourceDiscoveryItemRow)
                    .where(SourceDiscoveryItemRow.discovery_id == row.id)
                    .order_by(SourceDiscoveryItemRow.position)
                )
            ).all()
        )
        return SourceDiscoverySnapshot(
            id=row.id,
            owner_hash=row.owner_hash,
            request_fingerprint=row.request_fingerprint,
            encrypted_url=EncryptedUrl(
                ciphertext=row.url_ciphertext,
                nonce=row.url_nonce,
                key_id=row.url_key_id,
            ),
            source_fingerprint=row.source_fingerprint,
            provider_key=row.provider_key,
            title=row.title,
            adapter_version=row.adapter_version,
            status=DiscoveryStatus(row.status),
            expires_at=row.expires_at,
            created_at=row.created_at,
            items=tuple(
                SourceDiscoveryItemSnapshot(
                    item_ref=item.item_ref,
                    position=item.position,
                    kind=DiscoveryItemKind(item.kind),
                    child_provider=item.child_provider,
                    title=item.title,
                    duration_ms=item.duration_ms,
                    identity_evidence_hash=item.identity_evidence_hash,
                    decision_hint=DiscoveryDecisionHint(item.decision_hint),
                    status=DiscoveryItemStatus(item.status),
                )
                for item in items
            ),
        )

    @staticmethod
    async def _existing(
        session: AsyncSession, command: SourceDiscoveryCreate
    ) -> SourceDiscoveryRow | None:
        row = await session.scalar(
            select(SourceDiscoveryRow).where(
                SourceDiscoveryRow.owner_hash == command.owner_hash,
                SourceDiscoveryRow.idempotency_key == command.idempotency_key,
            )
        )
        if row is not None and row.request_fingerprint != command.request_fingerprint:
            raise SourceDiscoveryIdempotencyConflict(
                "source discovery idempotency key already used"
            )
        return row
