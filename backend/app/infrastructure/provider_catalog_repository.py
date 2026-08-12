"""SQLAlchemy persistence for the administrator-managed Provider catalog."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.provider_catalog import (
    DuplicateProviderCatalogKeyError,
    ProviderCatalogEntry,
)
from app.infrastructure.database.base import as_utc
from app.infrastructure.database.models import ProviderCatalogEntryRow


class SqlAlchemyProviderCatalogRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_entries(
        self, *, visible_only: bool = False
    ) -> tuple[ProviderCatalogEntry, ...]:
        filters = [ProviderCatalogEntryRow.is_deleted.is_(False)]
        if visible_only:
            filters.append(ProviderCatalogEntryRow.is_visible.is_(True))
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(ProviderCatalogEntryRow)
                    .where(*filters)
                    .order_by(
                        ProviderCatalogEntryRow.sort_order,
                        ProviderCatalogEntryRow.key,
                    )
                )
            ).all()
        return tuple(_to_domain(row) for row in rows)

    async def create_entry(
        self,
        *,
        key: str,
        display_name: str,
        sort_order: int,
        is_visible: bool,
        now: datetime,
    ) -> ProviderCatalogEntry:
        try:
            async with self._sessions.begin() as session:
                existing = await session.get(ProviderCatalogEntryRow, key)
                if existing is not None and not existing.is_deleted:
                    raise DuplicateProviderCatalogKeyError
                if existing is None:
                    row = ProviderCatalogEntryRow(
                        key=key,
                        display_name=display_name,
                        sort_order=sort_order,
                        is_visible=is_visible,
                        is_deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(row)
                    await session.flush()
                else:
                    existing.display_name = display_name
                    existing.sort_order = sort_order
                    existing.is_visible = is_visible
                    existing.is_deleted = False
                    existing.created_at = now
                    existing.updated_at = now
                    row = existing
        except IntegrityError as exc:
            raise DuplicateProviderCatalogKeyError from exc
        return _to_domain(row)

    async def update_entry(
        self,
        key: str,
        *,
        display_name: str | None,
        sort_order: int | None,
        is_visible: bool | None,
        now: datetime,
    ) -> ProviderCatalogEntry | None:
        values: dict[str, object] = {"updated_at": now}
        if display_name is not None:
            values["display_name"] = display_name
        if sort_order is not None:
            values["sort_order"] = sort_order
        if is_visible is not None:
            values["is_visible"] = is_visible
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(ProviderCatalogEntryRow)
                .where(
                    ProviderCatalogEntryRow.key == key,
                    ProviderCatalogEntryRow.is_deleted.is_(False),
                )
                .values(**values)
                .returning(ProviderCatalogEntryRow)
            )
        return _to_domain(row) if row is not None else None

    async def delete_entry(self, key: str, *, now: datetime) -> bool:
        async with self._sessions.begin() as session:
            row = await session.scalar(
                update(ProviderCatalogEntryRow)
                .where(
                    ProviderCatalogEntryRow.key == key,
                    ProviderCatalogEntryRow.is_deleted.is_(False),
                )
                .values(is_deleted=True, is_visible=False, updated_at=now)
                .returning(ProviderCatalogEntryRow.key)
            )
        return row is not None


def _to_domain(row: ProviderCatalogEntryRow) -> ProviderCatalogEntry:
    return ProviderCatalogEntry(
        key=row.key,
        display_name=row.display_name,
        sort_order=row.sort_order,
        is_visible=row.is_visible,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )
