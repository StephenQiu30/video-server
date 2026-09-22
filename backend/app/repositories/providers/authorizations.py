"""Short transactions serialize source maintenance and fence terminal results."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.provider_authorization import ProviderAuthorizationRow
from app.services.provider_authorization import (
    AuthorizationRecord,
    ProviderAuthorizationError,
    ProviderAuthorizationStatus,
)
from app.services.provider_types import ProviderAuthorizationSource


class ProviderAuthorizationRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def accept(
        self,
        user_id: UUID,
        provider_key: str,
        source: ProviderAuthorizationSource,
        *,
        now: datetime,
        ttl: timedelta,
        retention: timedelta,
    ) -> tuple[AuthorizationRecord, bool]:
        async with self._sessions() as session, session.begin():
            # Source maintenance is exclusive per provider across all API replicas.
            await session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"provider-authorization:{provider_key}"},
            )
            active = await session.scalar(
                select(ProviderAuthorizationRow)
                .where(
                    ProviderAuthorizationRow.provider_key == provider_key,
                    ProviderAuthorizationRow.status
                    == ProviderAuthorizationStatus.PENDING,
                )
                .with_for_update()
            )
            if active is not None and active.expires_at <= now:
                active.status = ProviderAuthorizationStatus.EXPIRED
                active.updated_at = now
                await session.flush()
                active = None
            if active is not None:
                if active.user_id != user_id or active.source != source.value:
                    raise ProviderAuthorizationError(
                        "provider_authorization_unavailable",
                        "该平台已有管理员授权事务正在进行，请等待其完成或取消后重试。",
                    )
                return _record(active), False
            row = ProviderAuthorizationRow(
                id=uuid4(),
                user_id=user_id,
                provider_key=provider_key,
                source=source.value,
                purpose="maintain_deployment_source",
                status=ProviderAuthorizationStatus.PENDING,
                expires_at=now + ttl,
                retain_until=now + ttl + retention,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.flush()
            return _record(row), True

    async def get(
        self, transaction_id: UUID, user_id: UUID, *, now: datetime
    ) -> AuthorizationRecord:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ProviderAuthorizationRow).where(
                    ProviderAuthorizationRow.id == transaction_id,
                    ProviderAuthorizationRow.user_id == user_id,
                    ProviderAuthorizationRow.retain_until > now,
                )
            )
            if row is None:
                raise ProviderAuthorizationError(
                    "not_found", "授权事务不存在或已经过期。"
                )
            return _record(row)

    async def transition(
        self, record: AuthorizationRecord, target: str, *, now: datetime
    ) -> AuthorizationRecord:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(ProviderAuthorizationRow)
                .where(
                    ProviderAuthorizationRow.id == record.id,
                    ProviderAuthorizationRow.user_id == record.user_id,
                )
                .with_for_update()
            )
            if row is None:
                raise ProviderAuthorizationError(
                    "not_found", "授权事务不存在或已经过期。"
                )
            if row.status == ProviderAuthorizationStatus.PENDING:
                row.status = (
                    ProviderAuthorizationStatus.EXPIRED
                    if row.expires_at <= now
                    else target
                )
                row.updated_at = now
            return _record(row)

    async def pending(self, *, limit: int = 100) -> tuple[AuthorizationRecord, ...]:
        if not 1 <= limit <= 200:
            raise ValueError("invalid authorization batch limit")
        async with self._sessions() as session:
            rows = await session.scalars(
                select(ProviderAuthorizationRow)
                .where(
                    ProviderAuthorizationRow.status
                    == ProviderAuthorizationStatus.PENDING,
                )
                .order_by(
                    ProviderAuthorizationRow.updated_at, ProviderAuthorizationRow.id
                )
                .limit(limit)
            )
            return tuple(_record(row) for row in rows)

    async def expired_results(
        self, *, now: datetime, limit: int = 100
    ) -> tuple[AuthorizationRecord, ...]:
        if not 1 <= limit <= 200:
            raise ValueError("invalid authorization cleanup limit")
        async with self._sessions() as session:
            rows = await session.scalars(
                select(ProviderAuthorizationRow)
                .where(
                    ProviderAuthorizationRow.status
                    != ProviderAuthorizationStatus.PENDING,
                    ProviderAuthorizationRow.retain_until <= now,
                )
                .order_by(ProviderAuthorizationRow.retain_until)
                .limit(limit)
            )
            return tuple(_record(row) for row in rows)

    async def forget(self, record: AuthorizationRecord, *, now: datetime) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                delete(ProviderAuthorizationRow).where(
                    ProviderAuthorizationRow.id == record.id,
                    ProviderAuthorizationRow.status
                    != ProviderAuthorizationStatus.PENDING,
                    ProviderAuthorizationRow.retain_until <= now,
                )
            )


def _record(row: ProviderAuthorizationRow) -> AuthorizationRecord:
    return AuthorizationRecord(
        row.id,
        row.user_id,
        row.provider_key,
        ProviderAuthorizationSource(row.source),
        row.status,
        row.expires_at,
    )
