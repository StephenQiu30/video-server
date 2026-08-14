from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from app.application.auth import AuthError, AuthErrorCode, CurrentUser, UserRole
from app.application.downloads import (
    ApplicationError,
    ApplicationErrorCode,
    DownloadAnalyticsDailySnapshot,
    DownloadAnalyticsSnapshot,
    DownloadAnalyticsSourceSnapshot,
    DownloadAnalyticsSummarySnapshot,
    GetDownloadAnalytics,
)
from app.application.downloads.analytics import _success_rate

NOW = datetime(2026, 8, 10, 12, 30, tzinfo=UTC)
ADMIN = CurrentUser(
    id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    username="admin_user",
    email="admin@example.com",
    role=UserRole.ADMIN,
    created_at=NOW,
    updated_at=NOW,
)
USER = CurrentUser(
    id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    username="normal_user",
    email="user@example.com",
    role=UserRole.USER,
    created_at=NOW,
    updated_at=NOW,
)


class AnalyticsRepository:
    def __init__(self, snapshot: DownloadAnalyticsSnapshot) -> None:
        self.snapshot = snapshot
        self.calls: list[tuple[datetime, datetime]] = []

    async def get_download_analytics(
        self, *, start: datetime, end: datetime
    ) -> DownloadAnalyticsSnapshot:
        self.calls.append((start, end))
        return self.snapshot


def analytics_snapshot() -> DownloadAnalyticsSnapshot:
    return DownloadAnalyticsSnapshot(
        summary=DownloadAnalyticsSummarySnapshot(
            total=6,
            succeeded=3,
            failed=1,
            cancelled=1,
            active=1,
            unique_users=4,
            downloaded_bytes=12_345,
            duration_seconds=630,
        ),
        daily=(
            DownloadAnalyticsDailySnapshot(
                date=date(2026, 8, 8),
                total=2,
                succeeded=1,
                failed=1,
                cancelled=0,
            ),
        ),
        sources=(
            DownloadAnalyticsSourceSnapshot(
                source_key="youtube",
                total=4,
                succeeded=3,
                failed=1,
                cancelled=0,
                active=0,
                unique_users=3,
                downloaded_bytes=12_345,
            ),
            DownloadAnalyticsSourceSnapshot(
                source_key="<untrusted-extractor>",
                total=2,
                succeeded=0,
                failed=0,
                cancelled=1,
                active=1,
                unique_users=1,
                downloaded_bytes=0,
            ),
            DownloadAnalyticsSourceSnapshot(
                source_key="browser_import",
                total=1,
                succeeded=1,
                failed=0,
                cancelled=0,
                active=0,
                unique_users=1,
                downloaded_bytes=1_024,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_download_analytics_builds_safe_visualization_view() -> None:
    repository = AnalyticsRepository(analytics_snapshot())
    use_case = GetDownloadAnalytics(repository, now=lambda: NOW)  # type: ignore[arg-type]

    view = await use_case(ADMIN, days=7)

    assert (view.period_days, view.start, view.end) == (
        7,
        datetime(2026, 8, 4, tzinfo=UTC),
        NOW,
    )
    assert repository.calls == [(view.start, view.end)]
    assert view.summary.average_duration_seconds == 105.0
    assert view.summary.success_rate == 75.0
    assert len(view.daily) == 7
    assert view.daily[0].date == date(2026, 8, 4)
    assert view.daily[0].total == 0
    assert view.daily[4].total == 2
    assert [(item.source_key, item.source_name) for item in view.sources] == [
        ("youtube", "YouTube"),
        ("other", "其他来源"),
        ("browser_import", "本地视频上传"),
    ]
    assert view.sources[0].success_rate == 75.0
    assert view.sources[1].success_rate == 0.0


@pytest.mark.parametrize("days", [0, 6, 366])
@pytest.mark.asyncio
async def test_download_analytics_rejects_out_of_range_period(days: int) -> None:
    repository = AnalyticsRepository(analytics_snapshot())
    use_case = GetDownloadAnalytics(repository, now=lambda: NOW)  # type: ignore[arg-type]

    with pytest.raises(ApplicationError) as error:
        await use_case(ADMIN, days=days)

    assert error.value.code is ApplicationErrorCode.INVALID_REQUEST
    assert repository.calls == []


@pytest.mark.asyncio
async def test_download_analytics_rejects_non_admin_before_querying() -> None:
    repository = AnalyticsRepository(analytics_snapshot())
    use_case = GetDownloadAnalytics(repository, now=lambda: NOW)  # type: ignore[arg-type]

    with pytest.raises(AuthError) as error:
        await use_case(USER, days=7)

    assert error.value.code is AuthErrorCode.FORBIDDEN
    assert repository.calls == []


def test_download_analytics_uses_half_up_success_rate_rounding() -> None:
    assert _success_rate(1, 15) == 6.3
