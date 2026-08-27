from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.api.dependencies import DownloadUseCases, SourceDiscoveryUseCases
from app.application.downloads import (
    ApplicationError,
    DownloadAnalyticsDailyView,
    DownloadAnalyticsSourceView,
    DownloadAnalyticsSummaryView,
    DownloadAnalyticsView,
    DownloadHistoryItemView,
    DownloadHistorySummaryView,
    DownloadHistoryView,
    DownloadUrl,
    DownloadView,
    FormatView,
    InspectionView,
    ThumbnailContent,
)
from app.application.source_discoveries import (
    SourceDiscoveryItemView,
    SourceDiscoveryView,
)
from app.domain.downloads import (
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DownloadPlan,
    DownloadStatus,
    DynamicRange,
    FpsBucket,
    ProviderHints,
    VideoCodecFamily,
)
from app.domain.source_discovery import (
    DiscoveryDecisionHint,
    DiscoveryItemKind,
    DiscoveryItemStatus,
    DiscoveryStatus,
)

NOW = datetime(2026, 8, 6, 10, tzinfo=UTC)
INSPECTION_ID = UUID("11111111-1111-4111-8111-111111111111")
FORMAT_ID = UUID("22222222-2222-4222-8222-222222222222")
JOB_ID = UUID("33333333-3333-4333-8333-333333333333")
DISCOVERY_ID = UUID("44444444-4444-4444-8444-444444444444")
ITEM_REF = UUID("55555555-5555-4555-8555-555555555555")


class StubUseCase:
    def __init__(self, result: object) -> None:
        self.result = result
        self.error: ApplicationError | None = None
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.result


def inspection_view() -> InspectionView:
    plan = DownloadPlan(
        height=1080,
        width=1920,
        fps_bucket=FpsBucket.FPS_30,
        dynamic_range=DynamicRange.SDR,
        video_codec_family=VideoCodecFamily.H264,
        audio_codec_family=AudioCodecFamily.AAC,
        audio_language="zh-CN",
        container_preference=ContainerPreference.MP4,
        compatibility_profile=CompatibilityProfile.BALANCED,
        hints=ProviderHints(video_id="private-v", audio_id="private-a"),
    )
    return InspectionView(
        id=INSPECTION_ID,
        extractor_key="Controlled",
        provider_media_id="video-1",
        title="Owned video",
        duration_seconds=30,
        expires_at=NOW + timedelta(minutes=15),
        formats=(FormatView(FORMAT_ID, "1080p MP4", plan),),
    )


def download_view(status: DownloadStatus = DownloadStatus.QUEUED) -> DownloadView:
    return DownloadView(
        id=JOB_ID,
        inspection_id=INSPECTION_ID,
        format_id=FORMAT_ID,
        status=status,
        stage=None,
        progress=100 if status is DownloadStatus.SUCCEEDED else 0,
        attempt=1 if status is DownloadStatus.SUCCEEDED else 0,
        error_code=None,
        created_at=NOW,
        updated_at=NOW,
        finished_at=NOW
        if status in {DownloadStatus.SUCCEEDED, DownloadStatus.CANCELLED}
        else None,
    )


def history_view() -> DownloadHistoryView:
    return DownloadHistoryView(
        items=(
            DownloadHistoryItemView(
                id=JOB_ID,
                title="Owned video",
                thumbnail_url=f"/api/inspections/{INSPECTION_ID}/thumbnail",
                format_name="1080p MP4",
                status=DownloadStatus.SUCCEEDED,
                progress=100,
                error_code=None,
                created_at=NOW,
                updated_at=NOW,
                finished_at=NOW,
            ),
        ),
        page=1,
        page_size=20,
        total=1,
        summary=DownloadHistorySummaryView(
            total=1,
            succeeded=1,
            active=0,
            failed=0,
        ),
    )


def analytics_view() -> DownloadAnalyticsView:
    return DownloadAnalyticsView(
        period_days=7,
        start=datetime(2026, 7, 31, tzinfo=UTC),
        end=NOW,
        summary=DownloadAnalyticsSummaryView(
            total=4,
            succeeded=3,
            failed=1,
            cancelled=0,
            active=0,
            unique_users=2,
            downloaded_bytes=12_345,
            average_duration_seconds=90.5,
            success_rate=75.0,
        ),
        daily=(
            DownloadAnalyticsDailyView(
                date=date(2026, 8, 6),
                total=4,
                succeeded=3,
                failed=1,
                cancelled=0,
            ),
        ),
        sources=(
            DownloadAnalyticsSourceView(
                source_key="youtube",
                source_name="YouTube",
                total=4,
                succeeded=3,
                failed=1,
                cancelled=0,
                active=0,
                unique_users=2,
                downloaded_bytes=12_345,
                success_rate=75.0,
            ),
        ),
    )


def source_discovery_view() -> SourceDiscoveryView:
    return SourceDiscoveryView(
        id=DISCOVERY_ID,
        provider_key="wechat_official_account_article",
        title="Article",
        status=DiscoveryStatus.READY,
        expires_at=NOW + timedelta(minutes=15),
        items=(
            SourceDiscoveryItemView(
                item_ref=ITEM_REF,
                kind=DiscoveryItemKind.WECHAT_CHANNELS,
                title="Channels item",
                duration_ms=None,
                decision_hint=DiscoveryDecisionHint.EXPORT_REQUIRED,
                status=DiscoveryItemStatus.READY,
            ),
        ),
    )


def source_discovery_use_cases() -> tuple[
    SourceDiscoveryUseCases, dict[str, StubUseCase]
]:
    stubs = {
        "create_discovery": StubUseCase(source_discovery_view()),
        "get_discovery": StubUseCase(source_discovery_view()),
    }
    return (
        SourceDiscoveryUseCases(
            create=stubs["create_discovery"],
            get=stubs["get_discovery"],
        ),
        stubs,
    )


def use_cases() -> tuple[DownloadUseCases, dict[str, StubUseCase]]:
    stubs = {
        "inspect": StubUseCase(inspection_view()),
        "inspect_discovered": StubUseCase(inspection_view()),
        "get_inspection": StubUseCase(inspection_view()),
        "get_thumbnail": StubUseCase(
            ThumbnailContent(b"image", "image/jpeg", "a" * 64)
        ),
        "create": StubUseCase(download_view()),
        "get": StubUseCase(download_view()),
        "cancel": StubUseCase(download_view(DownloadStatus.CANCELLED)),
        "retry": StubUseCase(download_view()),
        "issue_url": StubUseCase(
            DownloadUrl(
                "https://objects.example/token",
                NOW + timedelta(minutes=5),
            )
        ),
        "history": StubUseCase(history_view()),
        "analytics": StubUseCase(analytics_view()),
    }
    container = DownloadUseCases(
        inspect_media=stubs["inspect"],
        inspect_discovered_item=stubs["inspect_discovered"],
        get_inspection=stubs["get_inspection"],
        get_thumbnail=stubs["get_thumbnail"],
        create_download=stubs["create"],
        get_download=stubs["get"],
        cancel_download=stubs["cancel"],
        retry_download=stubs["retry"],
        issue_download_url=stubs["issue_url"],
        get_download_history=stubs["history"],
        get_download_analytics=stubs["analytics"],
    )
    return container, stubs
