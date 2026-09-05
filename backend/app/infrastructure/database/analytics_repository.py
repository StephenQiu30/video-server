"""Bounded aggregate queries for administrator download reporting."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import case, func, select
from sqlalchemy.engine import Row
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from app.application.downloads.source_catalog import (
    BROWSER_IMPORT_DOWNLOAD_SOURCE,
    DOWNLOAD_SOURCES,
    OTHER_DOWNLOAD_SOURCE,
)

from .analytics_contracts import (
    DownloadAnalyticsDailySnapshot,
    DownloadAnalyticsSnapshot,
    DownloadAnalyticsSourceSnapshot,
    DownloadAnalyticsSummarySnapshot,
)
from .models import ArtifactRow, DownloadJobRow, MediaInspectionRow
from .repository_base import RepositoryBase

_ACTIVE_STATUSES = ("queued", "running", "retry_wait")


class AnalyticsRepository(RepositoryBase):
    async def get_download_analytics(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> DownloadAnalyticsSnapshot:
        if start >= end:
            raise ValueError("analytics start must be before end")
        async with self._sessions() as session:
            summary = await session.execute(_summary_statement(start, end))
            daily = await session.execute(_daily_statement(start, end))
            sources = await session.execute(_source_statement(start, end))
        return DownloadAnalyticsSnapshot(
            summary=_summary_snapshot(summary.one()),
            daily=tuple(_daily_snapshot(row) for row in daily.all()),
            sources=tuple(_source_snapshot(row) for row in sources.all()),
        )


def _base_statement(*columns: Any) -> Select[Any]:
    return (
        select(*columns)
        .select_from(DownloadJobRow)
        .outerjoin(
            MediaInspectionRow,
            MediaInspectionRow.id == DownloadJobRow.inspection_id,
        )
        .outerjoin(ArtifactRow, ArtifactRow.job_id == DownloadJobRow.id)
    )


def _period(statement: Select[Any], start: datetime, end: datetime) -> Select[Any]:
    return statement.where(
        DownloadJobRow.created_at >= start,
        DownloadJobRow.created_at <= end,
    )


def _count_status(status: str) -> ColumnElement[int]:
    return func.sum(case((DownloadJobRow.status == status, 1), else_=0))


def _count_active() -> ColumnElement[int]:
    return func.sum(case((DownloadJobRow.status.in_(_ACTIVE_STATUSES), 1), else_=0))


def _summary_statement(start: datetime, end: datetime) -> Select[Any]:
    return _period(
        _base_statement(
            func.count(DownloadJobRow.id),
            _count_status("succeeded"),
            _count_status("failed"),
            _count_status("cancelled"),
            _count_active(),
            func.count(func.distinct(DownloadJobRow.owner_hash)),
            func.coalesce(func.sum(ArtifactRow.size_bytes), 0),
            func.coalesce(
                func.sum(
                    case(
                        (
                            DownloadJobRow.source_kind == "browser_import",
                            ArtifactRow.duration_ms,
                        ),
                        else_=MediaInspectionRow.duration_seconds * 1000,
                    )
                ),
                0,
            ),
        ),
        start,
        end,
    )


def _daily_statement(start: datetime, end: datetime) -> Select[Any]:
    day = _utc_day().label("day")
    statement = _base_statement(
        day,
        func.count(DownloadJobRow.id),
        _count_status("succeeded"),
        _count_status("failed"),
        _count_status("cancelled"),
    )
    return _period(statement, start, end).group_by(day).order_by(day)


def _source_statement(start: datetime, end: datetime) -> Select[Any]:
    source = _source_key().label("source_key")
    total = func.count(DownloadJobRow.id).label("total")
    statement = _base_statement(
        source,
        total,
        _count_status("succeeded"),
        _count_status("failed"),
        _count_status("cancelled"),
        _count_active(),
        func.count(func.distinct(DownloadJobRow.owner_hash)),
        func.coalesce(func.sum(ArtifactRow.size_bytes), 0),
    )
    return (
        _period(statement, start, end).group_by(source).order_by(total.desc(), source)
    )


def _utc_day() -> ColumnElement[date]:
    value = func.timezone("UTC", DownloadJobRow.created_at)
    return cast(ColumnElement[date], func.date(value))


def _source_key() -> ColumnElement[str]:
    extractor = func.lower(MediaInspectionRow.extractor_key)
    matches = tuple(
        (extractor.like(f"{prefix}%"), source.key)
        for source in DOWNLOAD_SOURCES
        for prefix in source.extractor_prefixes
    )
    return case(
        (
            DownloadJobRow.source_kind == "browser_import",
            BROWSER_IMPORT_DOWNLOAD_SOURCE.key,
        ),
        *matches,
        else_=OTHER_DOWNLOAD_SOURCE.key,
    )


def _summary_snapshot(row: Row[Any]) -> DownloadAnalyticsSummarySnapshot:
    *counts, duration_milliseconds = row
    values = tuple(_integer(value) for value in counts)
    return DownloadAnalyticsSummarySnapshot(
        total=values[0],
        succeeded=values[1],
        failed=values[2],
        cancelled=values[3],
        active=values[4],
        unique_users=values[5],
        downloaded_bytes=values[6],
        duration_seconds=_integer(duration_milliseconds) // 1000,
    )


def _daily_snapshot(row: Row[Any]) -> DownloadAnalyticsDailySnapshot:
    raw_date, *counts = row
    return DownloadAnalyticsDailySnapshot(
        date=_date(raw_date),
        total=_integer(counts[0]),
        succeeded=_integer(counts[1]),
        failed=_integer(counts[2]),
        cancelled=_integer(counts[3]),
    )


def _source_snapshot(row: Row[Any]) -> DownloadAnalyticsSourceSnapshot:
    source_key, *counts = row
    return DownloadAnalyticsSourceSnapshot(
        source_key=str(source_key),
        total=_integer(counts[0]),
        succeeded=_integer(counts[1]),
        failed=_integer(counts[2]),
        cancelled=_integer(counts[3]),
        active=_integer(counts[4]),
        unique_users=_integer(counts[5]),
        downloaded_bytes=_integer(counts[6]),
    )


def _integer(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ValueError("database returned a non-integral analytics count")
        return int(value)
    if isinstance(value, (int, float, str)):
        return int(value)
    raise ValueError("database returned an invalid analytics count")


def _date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError("database returned an invalid analytics date")
