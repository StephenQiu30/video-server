from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.infrastructure.database import SqlAlchemyDownloadRepository
from app.infrastructure.database.analytics_repository import _integer
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from tests.unit.infrastructure.analytics_helpers import (
    END,
    START,
    add_browser_import,
    add_job,
)


@pytest.fixture
async def analytics_database(postgres_engine: AsyncEngine):
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    yield SqlAlchemyDownloadRepository(sessions), sessions


@pytest.mark.asyncio
async def test_download_analytics_aggregates_period_sources_and_artifacts(
    analytics_database,
) -> None:
    repository, sessions = analytics_database
    owner_a, owner_b, owner_c = "a" * 64, "b" * 64, "c" * 64
    await add_job(
        sessions,
        extractor="Youtube",
        owner=owner_a,
        status="succeeded",
        created_at=datetime(2026, 8, 10, 10, tzinfo=UTC),
        duration=100,
        size_bytes=1_000,
    )
    await add_job(
        sessions,
        extractor="YoutubeTab",
        owner=owner_a,
        status="failed",
        created_at=datetime(2026, 8, 9, 10, tzinfo=UTC),
        duration=200,
        source_expires_at=datetime(2026, 8, 9, 11, tzinfo=UTC),
    )
    await add_job(
        sessions,
        extractor="BiliIntl",
        owner=owner_b,
        status="succeeded",
        created_at=datetime(2026, 8, 9, 12, tzinfo=UTC),
        duration=300,
        size_bytes=2_000,
    )
    await add_job(
        sessions,
        extractor="UnlistedExtractor",
        owner=owner_b,
        status="cancelled",
        created_at=datetime(2026, 8, 8, 10, tzinfo=UTC),
        duration=400,
    )
    await add_job(
        sessions,
        extractor="<untrusted>",
        owner=owner_c,
        status="running",
        created_at=datetime(2026, 8, 8, 12, tzinfo=UTC),
        duration=500,
    )
    await add_job(
        sessions,
        extractor="Youtube",
        owner=owner_c,
        status="succeeded",
        created_at=datetime(2026, 8, 1, 12, tzinfo=UTC),
        duration=900,
        size_bytes=9_000,
    )

    analytics = await repository.get_download_analytics(start=START, end=END)

    assert analytics.summary.total == 5
    assert (
        analytics.summary.succeeded,
        analytics.summary.failed,
        analytics.summary.cancelled,
        analytics.summary.active,
    ) == (2, 1, 1, 1)
    assert analytics.summary.unique_users == 3
    assert analytics.summary.downloaded_bytes == 3_000
    assert analytics.summary.duration_seconds == 1_500
    daily = {item.date: item for item in analytics.daily}
    assert daily[datetime(2026, 8, 9, tzinfo=UTC).date()].total == 2
    assert daily[datetime(2026, 8, 8, tzinfo=UTC).date()].cancelled == 1
    sources = {item.source_key: item for item in analytics.sources}
    assert set(sources) == {"youtube", "bilibili", "other"}
    assert sources["youtube"].total == 2
    assert sources["youtube"].unique_users == 1
    assert sources["youtube"].downloaded_bytes == 1_000
    assert sources["bilibili"].downloaded_bytes == 2_000
    assert sources["other"].total == 2
    assert sources["other"].unique_users == 2
    assert "<untrusted>" not in sources


@pytest.mark.asyncio
async def test_download_analytics_includes_the_exact_end_timestamp(
    analytics_database,
) -> None:
    repository, sessions = analytics_database
    await add_job(
        sessions,
        extractor="Youtube",
        owner="a" * 64,
        status="succeeded",
        created_at=END,
        duration=30,
        size_bytes=300,
    )

    analytics = await repository.get_download_analytics(start=START, end=END)

    assert analytics.summary.total == 1
    assert analytics.summary.downloaded_bytes == 300


@pytest.mark.asyncio
async def test_download_analytics_recognizes_kuaishou_plugin(
    analytics_database,
) -> None:
    repository, sessions = analytics_database
    await add_job(
        sessions,
        extractor="KuaishouPublic",
        owner="k" * 64,
        status="succeeded",
        created_at=datetime(2026, 8, 10, 10, tzinfo=UTC),
        duration=22,
        size_bytes=2_661_003,
    )

    analytics = await repository.get_download_analytics(start=START, end=END)

    source = next(item for item in analytics.sources if item.source_key == "kuaishou")
    assert source.total == 1
    assert source.downloaded_bytes == 2_661_003


@pytest.mark.asyncio
async def test_download_analytics_includes_browser_imports_without_provider_data(
    analytics_database,
) -> None:
    repository, sessions = analytics_database
    await add_browser_import(
        sessions,
        owner="u" * 64,
        created_at=datetime(2026, 8, 10, 10, tzinfo=UTC),
        duration_ms=12_345,
        size_bytes=4_096,
    )

    analytics = await repository.get_download_analytics(start=START, end=END)

    assert analytics.summary.total == 1
    assert analytics.summary.succeeded == 1
    assert analytics.summary.downloaded_bytes == 4_096
    assert analytics.summary.duration_seconds == 12
    assert analytics.daily[0].total == 1
    source = analytics.sources[0]
    assert source.source_key == "browser_import"
    assert source.total == 1
    assert source.unique_users == 1
    assert source.downloaded_bytes == 4_096


@pytest.mark.asyncio
async def test_download_analytics_rejects_an_empty_period(analytics_database) -> None:
    repository, _sessions = analytics_database

    with pytest.raises(ValueError, match="start must be before end"):
        await repository.get_download_analytics(start=END, end=END)


def test_download_analytics_accepts_postgres_bigint_sum() -> None:
    assert _integer(Decimal("9876543210")) == 9_876_543_210

    with pytest.raises(ValueError, match="non-integral"):
        _integer(Decimal("1.5"))
