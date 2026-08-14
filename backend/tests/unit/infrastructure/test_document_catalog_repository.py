from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.application.documents import GetDocument, ListDocuments
from app.application.imports import (
    ImportApplicationError,
    ImportApplicationErrorCode,
    ImportResourceCreate,
)
from app.domain.imports import ContentKind, ImportSourceFormat
from app.infrastructure.database import (
    Base,
    SqlAlchemyDocumentCatalogRepository,
    SqlAlchemyDocumentImportRepository,
)
from app.infrastructure.database.models import DocumentRow
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

NOW = datetime(2026, 8, 14, 15, 0, tzinfo=UTC)
FIRST = UUID("66666666-6666-4666-8666-666666666666")
SECOND = UUID("77777777-7777-4777-8777-777777777777")
THIRD = UUID("88888888-8888-4888-8888-888888888888")
OWNER = "a" * 64
OTHER_OWNER = "b" * 64


def command(resource_id: UUID, owner_hash: str, key: str) -> ImportResourceCreate:
    return ImportResourceCreate(
        id=resource_id,
        owner_hash=owner_hash,
        idempotency_key=key,
        request_fingerprint=key.ljust(64, "c"),
        content_kind=ContentKind.SCREENPLAY,
        source_format=ImportSourceFormat.MARKDOWN,
        display_name=f"{key}.md",
        content_type=ImportSourceFormat.MARKDOWN.content_type,
        declared_size_bytes=1024,
        declared_sha256="d" * 64,
        rights_statement_version="content-rights-v1",
    )


@pytest.fixture
async def catalog_data():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    imports = SqlAlchemyDocumentImportRepository(sessions)
    await imports.create_resource(command(FIRST, OWNER, "first"), now=NOW)
    await imports.create_resource(
        command(SECOND, OWNER, "second"), now=NOW + timedelta(seconds=1)
    )
    await imports.create_resource(command(THIRD, OTHER_OWNER, "third"), now=NOW)
    yield SqlAlchemyDocumentCatalogRepository(sessions), sessions
    await engine.dispose()


async def test_catalog_is_owner_scoped_ordered_and_hides_deleted(catalog_data) -> None:
    catalog, sessions = catalog_data
    list_documents = ListDocuments(catalog)

    first_page = await list_documents(OWNER, page=1, page_size=1)
    second_page = await list_documents(OWNER, page=2, page_size=1)

    assert first_page.total == second_page.total == 2
    assert first_page.items[0].id == SECOND
    assert second_page.items[0].id == FIRST
    async with sessions() as session, session.begin():
        row = await session.get(DocumentRow, SECOND)
        assert row is not None
        row.deleted_at = NOW + timedelta(minutes=1)
    remaining = await list_documents(OWNER)
    assert remaining.total == 1
    assert tuple(item.id for item in remaining.items) == (FIRST,)


async def test_detail_maps_safe_metadata_and_hides_other_owner(catalog_data) -> None:
    catalog, _ = catalog_data
    get_document = GetDocument(catalog)

    view = await get_document(FIRST, OWNER)

    assert view.title == "first"
    assert view.original_filename == "first.md"
    assert view.source_format is ImportSourceFormat.MARKDOWN
    assert view.detected_language is None
    with pytest.raises(ImportApplicationError) as raised:
        await get_document(FIRST, OTHER_OWNER)
    assert raised.value.code is ImportApplicationErrorCode.NOT_FOUND


async def test_list_rejects_invalid_pagination(catalog_data) -> None:
    catalog, _ = catalog_data

    with pytest.raises(ImportApplicationError) as raised:
        await ListDocuments(catalog)(OWNER, page=0)

    assert raised.value.code is ImportApplicationErrorCode.INVALID_REQUEST
