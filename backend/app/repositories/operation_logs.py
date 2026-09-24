"""Persist before dispatch; finalize once, with bounded metadata only."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import false, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import utc_now
from app.models.operation_log import OperationLogRow
from app.services.auth.models import CurrentUser


@dataclass(frozen=True, slots=True)
class OperationLogPage:
    items: tuple[OperationLogRow, ...]
    total: int


class OperationLogStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def begin(
        self,
        *,
        operation: str,
        description: str,
        method: str,
        route: str,
        resource_id: UUID | None,
    ) -> UUID:
        entry_id = uuid4()
        async with self._sessions.begin() as session:
            session.add(
                OperationLogRow(
                    id=entry_id,
                    created_at=utc_now(),
                    operation=operation[:160],
                    description=description[:256],
                    method=method,
                    route=route[:256],
                    resource_id=resource_id,
                    outcome="started",
                )
            )
        return entry_id

    async def finish(
        self,
        entry_id: UUID,
        *,
        actor: CurrentUser | None,
        status_code: int | None,
        failed: bool,
        error_code: str | None,
        resource_id: UUID | None = None,
        resource_key: str | None = None,
    ) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(OperationLogRow)
                .where(
                    OperationLogRow.id == entry_id, OperationLogRow.outcome == "started"
                )
                .values(
                    finished_at=utc_now(),
                    actor_id=actor.id if actor else None,
                    actor_name=actor.username if actor else None,
                    outcome="failed" if failed else "succeeded",
                    status_code=status_code,
                    error_code=error_code,
                    resource_id=func.coalesce(OperationLogRow.resource_id, resource_id),
                    resource_key=resource_key,
                )
            )

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        q: str | None,
        outcome: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
        admin_only: bool,
        source: Literal["request", "task"] | None = None,
    ) -> OperationLogPage:
        criteria = []
        if q:
            query = q.strip()
            try:
                identifier = UUID(query)
            except ValueError:
                identifier = None
            criteria.append(
                or_(
                    OperationLogRow.resource_id == identifier
                    if identifier
                    else false(),
                    OperationLogRow.id == identifier if identifier else false(),
                    OperationLogRow.actor_id == identifier if identifier else false(),
                    OperationLogRow.actor_name.icontains(query, autoescape=True),
                    OperationLogRow.resource_key.icontains(query, autoescape=True),
                    OperationLogRow.operation.icontains(query, autoescape=True),
                    OperationLogRow.description.icontains(query, autoescape=True),
                )
            )
        if source:
            criteria.append(OperationLogRow.source == source)
        if outcome:
            criteria.append(OperationLogRow.outcome == outcome)
        if created_from:
            criteria.append(OperationLogRow.created_at >= created_from)
        if created_to:
            criteria.append(OperationLogRow.created_at <= created_to)
        if admin_only:
            criteria.append(OperationLogRow.route.startswith("/api/admin/"))
        async with self._sessions() as session:
            total = (
                await session.scalar(
                    select(func.count()).select_from(OperationLogRow).where(*criteria)
                )
                or 0
            )
            rows = (
                await session.scalars(
                    select(OperationLogRow)
                    .where(*criteria)
                    .order_by(
                        OperationLogRow.created_at.desc(), OperationLogRow.id.desc()
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
            return OperationLogPage(items=tuple(rows), total=total)
