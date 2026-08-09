from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.application.auth import AuthError, AuthErrorCode, CurrentUser, UserRole
from app.application.downloads.analytics_models import (
    DownloadAnalyticsDailySnapshot,
    DownloadAnalyticsDailyView,
    DownloadAnalyticsSourceSnapshot,
    DownloadAnalyticsSourceView,
    DownloadAnalyticsSummarySnapshot,
    DownloadAnalyticsSummaryView,
    DownloadAnalyticsView,
)
from app.application.downloads.errors import ApplicationError, ApplicationErrorCode
from app.application.downloads.ports import DownloadRepository
from app.application.downloads.source_catalog import download_source
from app.application.downloads.validation import validate_now


class GetDownloadAnalytics:
    def __init__(
        self,
        repository: DownloadRepository,
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._now = now

    async def __call__(
        self,
        actor: CurrentUser,
        *,
        days: int = 30,
    ) -> DownloadAnalyticsView:
        if actor.role is not UserRole.ADMIN:
            raise AuthError(AuthErrorCode.FORBIDDEN)
        if not 7 <= days <= 365:
            raise ApplicationError(ApplicationErrorCode.INVALID_REQUEST)
        end = validate_now(self._now()).astimezone(UTC)
        start = datetime.combine(
            end.date() - timedelta(days=days - 1),
            time.min,
            tzinfo=UTC,
        )
        snapshot = await self._repository.get_download_analytics(
            start=start,
            end=end,
        )
        return DownloadAnalyticsView(
            period_days=days,
            start=start,
            end=end,
            summary=_summary_view(snapshot.summary),
            daily=_daily_views(start.date(), days, snapshot.daily),
            sources=tuple(_source_view(item) for item in snapshot.sources),
        )


def _summary_view(
    value: DownloadAnalyticsSummarySnapshot,
) -> DownloadAnalyticsSummaryView:
    average = value.duration_seconds / value.total if value.total else 0.0
    return DownloadAnalyticsSummaryView(
        total=value.total,
        succeeded=value.succeeded,
        failed=value.failed,
        cancelled=value.cancelled,
        active=value.active,
        unique_users=value.unique_users,
        downloaded_bytes=value.downloaded_bytes,
        average_duration_seconds=round(average, 2),
        success_rate=_success_rate(value.succeeded, value.failed),
    )


def _daily_views(
    start: date,
    days: int,
    values: tuple[DownloadAnalyticsDailySnapshot, ...],
) -> tuple[DownloadAnalyticsDailyView, ...]:
    by_date = {item.date: item for item in values}
    return tuple(
        _daily_view(
            current,
            by_date.get(current),
        )
        for offset in range(days)
        for current in (start + timedelta(days=offset),)
    )


def _daily_view(
    current: date,
    value: DownloadAnalyticsDailySnapshot | None,
) -> DownloadAnalyticsDailyView:
    return DownloadAnalyticsDailyView(
        date=current,
        total=0 if value is None else value.total,
        succeeded=0 if value is None else value.succeeded,
        failed=0 if value is None else value.failed,
        cancelled=0 if value is None else value.cancelled,
    )


def _source_view(value: DownloadAnalyticsSourceSnapshot) -> DownloadAnalyticsSourceView:
    source = download_source(value.source_key)
    return DownloadAnalyticsSourceView(
        source_key=source.key,
        source_name=source.name,
        total=value.total,
        succeeded=value.succeeded,
        failed=value.failed,
        cancelled=value.cancelled,
        active=value.active,
        unique_users=value.unique_users,
        downloaded_bytes=value.downloaded_bytes,
        success_rate=_success_rate(value.succeeded, value.failed),
    )


def _success_rate(succeeded: int, failed: int) -> float:
    completed = succeeded + failed
    if not completed:
        return 0.0
    percentage = Decimal(succeeded * 100) / Decimal(completed)
    return float(percentage.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
