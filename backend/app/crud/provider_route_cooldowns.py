"""Short row-locked transactions; no platform request holds a DB connection."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import func, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.provider_route_cooldown import ProviderRouteCooldownRow as Row
from app.services.provider_access import ProviderAccessPolicy
from app.services.provider_route_admission import (
    DEFAULT_COOLDOWN,
    PROBE_LEASE,
    ProviderRouteKey,
    ProviderRouteLease,
    RouteAdmissionUnavailable,
    RouteCoolingDown,
)


async def bound_route_transaction(session: AsyncSession) -> None:
    await session.execute(
        text(
            "SELECT set_config('lock_timeout', '1s', true), "
            "set_config('statement_timeout', '3s', true)"
        )
    )


def _identity(key: ProviderRouteKey) -> dict[str, str]:
    return dict(
        provider_key=key.provider_key,
        access_policy_id=key.access_policy_id.value,
        egress_binding_id=key.egress_binding_id,
    )


async def _locked(session: AsyncSession, key: ProviderRouteKey) -> Row | None:
    result = await session.execute(
        select(Row).filter_by(**_identity(key)).with_for_update()
    )
    return result.scalar_one_or_none()


def _retry_at(row: Row | None, now: datetime) -> datetime:
    return max(
        now + PROBE_LEASE,
        row.blocked_until if row and row.blocked_until else now,
        row.probe_lease_until if row and row.probe_lease_until else now,
    )


async def acquire_route(
    session: AsyncSession, key: ProviderRouteKey, owner: str
) -> ProviderRouteLease:
    row = await _locked(session, key)
    if row is None or row.blocked_until is None:
        return ProviderRouteLease(key, owner, None)
    now = await session.scalar(select(func.clock_timestamp()))
    assert now is not None
    if row.blocked_until > now:
        raise RouteCoolingDown(_retry_at(row, now))
    if row.probe_lease_until is not None and row.probe_lease_until > now:
        if row.probe_owner == owner:
            return ProviderRouteLease(key, owner, row.version, row.probe_lease_until)
        raise RouteCoolingDown(_retry_at(row, now))
    row.probe_owner, row.probe_lease_until = owner, now + PROBE_LEASE
    row.version += 1
    await session.flush()
    return ProviderRouteLease(key, owner, row.version, row.probe_lease_until)


class SqlAlchemyProviderRouteCooldowns:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]):
        self._sessions = sessions

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[AsyncSession]:
        try:
            async with self._sessions() as session, session.begin():
                await bound_route_transaction(session)
                yield session
        except SQLAlchemyError as error:
            raise RouteAdmissionUnavailable from error

    async def retry_times(
        self, keys: tuple[ProviderRouteKey, ...]
    ) -> dict[ProviderRouteKey, datetime]:
        if not keys:
            return {}
        async with self._transaction() as session:
            rows = await session.scalars(
                select(Row).where(
                    tuple_(
                        Row.provider_key, Row.access_policy_id, Row.egress_binding_id
                    ).in_(
                        [
                            (
                                key.provider_key,
                                key.access_policy_id.value,
                                key.egress_binding_id,
                            )
                            for key in keys
                        ]
                    ),
                    Row.blocked_until.is_not(None),
                )
            )
            return {
                ProviderRouteKey(
                    row.provider_key,
                    ProviderAccessPolicy(row.access_policy_id),
                    row.egress_binding_id,
                ): max(row.blocked_until, row.probe_lease_until or row.blocked_until)
                for row in rows
                if row.blocked_until is not None
            }

    async def acquire(self, key: ProviderRouteKey, owner: str) -> ProviderRouteLease:
        async with self._transaction() as session:
            return await acquire_route(session, key, owner)

    async def block(self, key: ProviderRouteKey, *, until: datetime) -> datetime:
        statement = insert(Row).values(
            **_identity(key),
            blocked_until=until,
            reason_code="provider_rate_limited",
            version=1,
        )
        returning = statement.on_conflict_do_update(
            index_elements=[
                Row.provider_key,
                Row.access_policy_id,
                Row.egress_binding_id,
            ],
            set_={
                "blocked_until": func.greatest(
                    Row.blocked_until, statement.excluded.blocked_until
                ),
                "probe_owner": None,
                "probe_lease_until": None,
                "version": Row.version + 1,
            },
        ).returning(Row.blocked_until)
        async with self._transaction() as session:
            result = (await session.execute(returning)).scalar_one()
            assert result is not None
            return result

    async def finish(self, lease: ProviderRouteLease, *, success: bool) -> None:
        async with self._transaction() as session:
            row = await _locked(session, lease.key)
            now = await session.scalar(select(func.clock_timestamp()))
            assert now is not None
            if (
                row is None
                or lease.version is None
                or row.version != lease.version
                or row.probe_owner != lease.owner
                or row.probe_lease_until is None
                or row.probe_lease_until <= now
            ):
                raise RouteCoolingDown(_retry_at(row, now))
            row.blocked_until = (
                None
                if success
                else max(row.blocked_until or now, now + DEFAULT_COOLDOWN)
            )
            row.probe_owner = row.probe_lease_until = None
            row.version += 1
