"""Short transactions own guest single-flight, global slots and fenced publication."""

from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.provider_guest_context import ProviderGuestContextRow as Row
from app.repositories.errors import LeaseConflict
from app.services.downloads.validation import validate_now
from app.services.provider_guest import (
    GuestContext,
    GuestMaintenanceLease,
    GuestScope,
    GuestState,
)

_PREPARING = ("preparing", "refreshing")
_REASONS = frozenset(
    {
        "provider_temporarily_unavailable",
        "provider_rate_limited",
        "provider_verification_required",
        "provider_guest_context_required",
        "provider_configuration_missing",
        "inspection_timeout",
    }
)


class GuestContexts:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def read(self, scope: GuestScope) -> GuestContext | None:
        async with self._sessions() as session:
            row = await session.get(Row, scope.key)
            return None if row is None else _snapshot(row, scope)

    async def claim(
        self, scope: GuestScope, owner: str, *, now: datetime
    ) -> GuestMaintenanceLease | None:
        validate_now(now)
        if not owner.strip() or len(owner) > 128:
            raise ValueError("invalid maintenance owner")
        async with self._sessions() as session, session.begin():
            await session.execute(text("SET LOCAL lock_timeout = '3s'"))
            # Covers counting and taking a slot across all Worker replicas. No
            # upstream work occurs while this transaction-level lock is held.
            await session.execute(text("SELECT pg_advisory_xact_lock(440903)"))
            await session.execute(
                insert(Row)
                .values(
                    id=scope.key,
                    provider_key=scope.provider.value,
                    profile_version=scope.profile_version,
                    client_profile_id=scope.client_profile_id,
                    egress_affinity_id=scope.egress_affinity_id,
                    updated_at=now,
                )
                .on_conflict_do_nothing()
            )
            row = await session.scalar(
                select(Row).where(Row.id == scope.key).with_for_update()
            )
            assert row is not None
            if (
                row.state == "revoked"
                or (row.lease_expires_at is not None and row.lease_expires_at > now)
                or (row.retry_at is not None and row.retry_at > now)
            ):
                return None
            if row.refresh_after is not None and row.refresh_after > now:
                return None
            active = (
                await session.scalars(
                    select(Row.provider_key).where(
                        Row.state.in_(_PREPARING), Row.lease_expires_at > now
                    )
                )
            ).all()
            if len(active) >= 2 or scope.provider.value in active:
                return None
            if row.valid_until is not None and row.valid_until <= now:
                _clear_material(row)
            row.state = "refreshing" if row.ciphertext is not None else "preparing"
            row.fence += 1
            row.lease_owner = owner
            row.lease_expires_at = now + timedelta(seconds=60)
            row.retry_at = None
            row.reason_code = None
            row.updated_at = now
            return GuestMaintenanceLease(
                scope, owner, row.fence, row.revision + 1, row.lease_expires_at
            )

    async def publish(
        self,
        lease: GuestMaintenanceLease,
        ciphertext: bytes,
        *,
        now: datetime,
        valid_until: datetime,
    ) -> GuestContext:
        validate_now(now)
        validate_now(valid_until)
        if not 0 < len(
            ciphertext
        ) <= 2 * 1024**2 or not now < valid_until <= now + timedelta(hours=1):
            raise ValueError("invalid guest publication budget")
        async with self._sessions() as session, session.begin():
            row = await _leased(session, lease, now)
            row.ciphertext = ciphertext
            row.valid_until = valid_until
            row.refresh_after = valid_until - min(
                timedelta(seconds=60), (valid_until - now) / 5
            )
            row.revision = lease.revision
            row.failures = 0
            _transition(row, "ready", now)
            return _snapshot(row, lease.scope)

    async def fail(
        self, lease: GuestMaintenanceLease, reason: str, *, now: datetime
    ) -> GuestContext:
        validate_now(now)
        if reason not in _REASONS:
            raise ValueError("guest failure must use a non-secret stable reason")
        async with self._sessions() as session, session.begin():
            row = await _leased(session, lease, now)
            row.failures += 1
            _transition(row, "cooling", now)
            row.reason_code = reason
            row.retry_at = now + timedelta(
                seconds=min(300, 30 * 2 ** min(row.failures - 1, 4))
            )
            if row.valid_until is not None and row.valid_until <= now:
                _clear_material(row)
            return _snapshot(row, lease.scope)

    async def invalidate(self, observed: GuestContext, *, now: datetime) -> bool:
        """Discard only the corrupt snapshot we read, never a newer publication."""
        validate_now(now)
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(Row).where(Row.id == observed.scope.key).with_for_update()
            )
            if (
                row is None
                or row.state == "revoked"
                or row.fence != observed.fence
                or row.revision != observed.revision
            ):
                return False
            row.fence += 1
            row.failures += 1
            _clear_material(row)
            _transition(row, "cooling", now)
            row.reason_code = "provider_guest_context_required"
            row.retry_at = now + timedelta(seconds=30)
            return True

    async def revoke(self, scope: GuestScope, *, now: datetime) -> None:
        validate_now(now)
        async with self._sessions() as session, session.begin():
            # A tombstone also prevents a maintainer racing first creation from
            # resurrecting a revoked scope.
            await session.execute(
                insert(Row)
                .values(
                    id=scope.key,
                    provider_key=scope.provider.value,
                    profile_version=scope.profile_version,
                    client_profile_id=scope.client_profile_id,
                    egress_affinity_id=scope.egress_affinity_id,
                    updated_at=now,
                )
                .on_conflict_do_nothing()
            )
            row = await session.scalar(
                select(Row).where(Row.id == scope.key).with_for_update()
            )
            assert row is not None
            row.fence += 1
            _clear_material(row)
            _transition(row, "revoked", now)

    async def recover(self, *, now: datetime, limit: int = 100) -> int:
        validate_now(now)
        if not 1 <= limit <= 200:
            raise ValueError("invalid guest recovery limit")
        async with self._sessions() as session, session.begin():
            rows = (
                await session.scalars(
                    select(Row)
                    .where(
                        ((Row.state.in_(_PREPARING)) & (Row.lease_expires_at <= now))
                        | ((Row.ciphertext.is_not(None)) & (Row.valid_until <= now))
                    )
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            for row in rows:
                if row.valid_until is not None and row.valid_until <= now:
                    _clear_material(row)
                if (
                    row.state in _PREPARING
                    and row.lease_expires_at is not None
                    and row.lease_expires_at <= now
                ):
                    row.fence += 1
                    row.failures += 1
                    _transition(row, "cooling", now)
                    row.retry_at = now + timedelta(seconds=30)
                    row.reason_code = "inspection_timeout"
                elif row.state == "ready":
                    _transition(row, "expired", now)
            return len(rows)


async def _leased(
    session: AsyncSession, lease: GuestMaintenanceLease, now: datetime
) -> Row:
    row = await session.scalar(
        select(Row)
        .where(
            Row.id == lease.scope.key,
            Row.state.in_(_PREPARING),
            Row.fence == lease.fence,
            Row.lease_owner == lease.owner,
            Row.revision == lease.revision - 1,
            Row.lease_expires_at > now,
        )
        .with_for_update()
    )
    if row is None:
        raise LeaseConflict("guest maintenance lease lost")
    return row


def _clear_material(row: Row) -> None:
    row.ciphertext = None
    row.valid_until = None
    row.refresh_after = None


def _transition(row: Row, state: str, now: datetime) -> None:
    row.state = state
    row.lease_owner = None
    row.lease_expires_at = None
    row.retry_at = None
    row.reason_code = None
    row.updated_at = now


def _snapshot(row: Row, scope: GuestScope) -> GuestContext:
    return GuestContext(
        scope,
        cast(GuestState, row.state),
        row.revision,
        row.fence,
        row.ciphertext,
        row.valid_until,
        row.refresh_after,
        row.retry_at,
        row.reason_code,
    )
