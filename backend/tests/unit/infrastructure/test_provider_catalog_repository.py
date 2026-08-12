from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.application.provider_catalog import DuplicateProviderCatalogKeyError
from app.infrastructure.database import Base, create_session_factory
from app.infrastructure.provider_catalog_repository import (
    SqlAlchemyProviderCatalogRepository,
)
from sqlalchemy.ext.asyncio import create_async_engine

NOW = datetime(2026, 8, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_catalog_repository_orders_filters_soft_deletes_and_revives() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    repository = SqlAlchemyProviderCatalogRepository(create_session_factory(engine))

    await repository.create_entry(
        key="hidden",
        display_name="Hidden",
        sort_order=20,
        is_visible=False,
        now=NOW,
    )
    await repository.create_entry(
        key="visible",
        display_name="Visible",
        sort_order=10,
        is_visible=True,
        now=NOW,
    )
    assert [item.key for item in await repository.list_entries()] == [
        "visible",
        "hidden",
    ]
    assert [item.key for item in await repository.list_entries(visible_only=True)] == [
        "visible"
    ]

    with pytest.raises(DuplicateProviderCatalogKeyError):
        await repository.create_entry(
            key="visible",
            display_name="Duplicate",
            sort_order=30,
            is_visible=True,
            now=NOW,
        )
    changed = await repository.update_entry(
        "visible",
        display_name="Renamed",
        sort_order=30,
        is_visible=False,
        now=NOW + timedelta(minutes=1),
    )
    assert changed is not None and changed.display_name == "Renamed"
    assert await repository.delete_entry("visible", now=NOW) is True
    assert await repository.delete_entry("visible", now=NOW) is False

    revived = await repository.create_entry(
        key="visible",
        display_name="Revived",
        sort_order=5,
        is_visible=True,
        now=NOW + timedelta(minutes=2),
    )
    assert revived.display_name == "Revived"
    assert [item.key for item in await repository.list_entries()] == [
        "visible",
        "hidden",
    ]
    await engine.dispose()
