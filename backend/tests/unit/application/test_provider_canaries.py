from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from app.application.provider_canaries import ProviderStatusService
from app.application.provider_catalog import ProviderCatalogEntry
from app.application.providers import ProviderStatusView
from app.domain.providers import (
    ProviderAccessMode,
    ProviderCanaryOutcome,
    ProviderCanaryResult,
    ProviderCanaryStage,
    ProviderCapability,
    ProviderSupportStatus,
)

NOW = datetime(2026, 8, 11, 6, tzinfo=UTC)


class Reader:
    def __init__(
        self,
        results: tuple[ProviderCanaryResult, ...],
        *,
        key: str = "vimeo",
    ) -> None:
        self.results = results
        self.key = key

    async def list_recent(
        self, *, limit_per_provider: int
    ) -> dict[str, tuple[ProviderCanaryResult, ...]]:
        assert limit_per_provider == 32
        return {self.key: self.results}


class Catalog:
    async def list_entries(
        self, *, visible_only: bool = False
    ) -> tuple[ProviderCatalogEntry, ...]:
        assert visible_only is True
        return (
            ProviderCatalogEntry(
                key="custom",
                display_name="Custom platform",
                sort_order=1,
                is_visible=True,
                created_at=NOW,
                updated_at=NOW,
            ),
            ProviderCatalogEntry(
                key="vimeo",
                display_name="Vimeo 视频",
                sort_order=2,
                is_visible=True,
                created_at=NOW,
                updated_at=NOW,
            ),
        )


def baseline(
    status: ProviderSupportStatus = ProviderSupportStatus.UNKNOWN,
) -> ProviderStatusView:
    return ProviderStatusView(
        key="vimeo",
        display_name="Vimeo",
        profile_version="1",
        registered=True,
        extractor_exists=True,
        capabilities=(ProviderCapability.SINGLE_VIDEO,),
        access_modes=(ProviderAccessMode.ANONYMOUS,),
        status=status,
        last_checked_at=None,
        last_check_succeeded=None,
        download_available=False,
        last_media_verified_at=None,
        last_verified_at=None,
        user_action="待验证",
    )


def result(
    minutes: int,
    *,
    stage: ProviderCanaryStage = ProviderCanaryStage.METADATA,
    error: str | None = None,
) -> ProviderCanaryResult:
    return ProviderCanaryResult(
        target_id="vimeo-owned-1",
        provider_key="vimeo",
        profile_version="1",
        stage=stage,
        access_mode=ProviderAccessMode.ANONYMOUS,
        outcome=(
            ProviderCanaryOutcome.FAILED
            if error is not None
            else ProviderCanaryOutcome.SUCCEEDED
        ),
        stable_error_code=error,
        checked_at=NOW - timedelta(minutes=minutes),
        duration_ms=100,
        engine_commit="5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc",
        egress_affinity_id="default",
        client_profile_id="yt-dlp-default",
    )


@pytest.mark.asyncio
async def test_unapproved_profile_stays_unknown_after_media_evidence() -> None:
    results = (
        result(0),
        result(15, stage=ProviderCanaryStage.ANALYSIS),
        result(30),
        result(60, stage=ProviderCanaryStage.MEDIA),
        result(90),
        result(120, error="inspection_timeout"),
    )
    service = ProviderStatusService(Reader(results), (baseline(),), now=lambda: NOW)

    view = (await service.list())[0]

    assert view.status is ProviderSupportStatus.UNKNOWN
    assert view.last_media_verified_at == NOW - timedelta(minutes=60)
    assert view.last_verified_at == NOW - timedelta(minutes=15)
    assert view.user_action == (
        "公开样本已完成真实下载验证；完整视频分析链路仍待验证。"
    )


@pytest.mark.asyncio
async def test_approved_profile_recovers_after_fresh_canary_evidence() -> None:
    results = (
        result(0),
        result(15, stage=ProviderCanaryStage.ANALYSIS),
        result(30),
        result(60, stage=ProviderCanaryStage.MEDIA),
        result(90),
        result(120, error="inspection_timeout"),
    )
    service = ProviderStatusService(
        Reader(results),
        (baseline(ProviderSupportStatus.VERIFIED),),
        now=lambda: NOW,
    )

    assert (await service.list())[0].status is ProviderSupportStatus.VERIFIED


@pytest.mark.asyncio
async def test_supported_download_is_explicit_with_conditional_session() -> None:
    results = (
        result(0),
        result(30, stage=ProviderCanaryStage.MEDIA),
    )
    service = ProviderStatusService(
        Reader(results),
        (baseline(ProviderSupportStatus.ACCESS_REQUIRED),),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.download_supported is True
    assert view.download_available is True
    assert view.status is ProviderSupportStatus.ACCESS_REQUIRED
    assert view.user_action == (
        "公开样本已完成真实下载；遇到平台挑战时才需要已批准的受控会话。"
    )


@pytest.mark.asyncio
async def test_approved_without_current_canary_is_not_reported_verified() -> None:
    service = ProviderStatusService(
        Reader(()),
        (baseline(ProviderSupportStatus.VERIFIED),),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.status is ProviderSupportStatus.UNKNOWN
    assert view.last_verified_at is None
    assert view.user_action == "该平台尚未完成当前版本的真实下载验证。"


@pytest.mark.asyncio
async def test_verified_baseline_requires_current_full_chain_evidence() -> None:
    service = ProviderStatusService(
        Reader((result(0), result(30, stage=ProviderCanaryStage.MEDIA))),
        (baseline(ProviderSupportStatus.VERIFIED),),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.status is ProviderSupportStatus.UNKNOWN
    assert view.last_checked_at == NOW
    assert view.last_check_succeeded is True
    assert view.download_available is True


@pytest.mark.asyncio
async def test_evidence_from_an_old_profile_version_is_ignored() -> None:
    old = replace(result(0), profile_version="old")
    service = ProviderStatusService(
        Reader((old,)),
        (baseline(ProviderSupportStatus.VERIFIED),),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.status is ProviderSupportStatus.UNKNOWN
    assert view.last_checked_at is None
    assert view.last_check_succeeded is None
    assert view.download_available is False


@pytest.mark.asyncio
async def test_latest_media_failure_revokes_download_availability() -> None:
    results = (
        result(0, stage=ProviderCanaryStage.MEDIA, error="download_timeout"),
        result(60, stage=ProviderCanaryStage.MEDIA),
    )
    service = ProviderStatusService(
        Reader(results),
        (baseline(),),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.last_check_succeeded is False
    assert view.download_available is False
    assert view.last_media_verified_at == NOW - timedelta(minutes=60)


@pytest.mark.asyncio
async def test_explicitly_approved_profile_promotes_only_with_full_chain() -> None:
    results = (
        result(0),
        result(15, stage=ProviderCanaryStage.ANALYSIS),
        result(30),
        result(60, stage=ProviderCanaryStage.MEDIA),
        result(90),
        result(120, error="inspection_timeout"),
    )
    service = ProviderStatusService(
        Reader(results),
        (baseline(),),
        now=lambda: NOW,
        approved_keys=frozenset({"vimeo"}),
    )

    assert (await service.list())[0].status is ProviderSupportStatus.VERIFIED


@pytest.mark.asyncio
async def test_explicit_approval_without_analysis_evidence_stays_unknown() -> None:
    results = (
        result(0),
        result(30),
        result(60, stage=ProviderCanaryStage.MEDIA),
        result(90),
        result(120, error="inspection_timeout"),
    )
    service = ProviderStatusService(
        Reader(results),
        (baseline(),),
        now=lambda: NOW,
        approved_keys=frozenset({"vimeo"}),
    )

    assert (await service.list())[0].status is ProviderSupportStatus.UNKNOWN


def test_rejects_approval_for_an_unregistered_provider() -> None:
    with pytest.raises(ValueError, match="not registered"):
        ProviderStatusService(
            Reader(()),
            (baseline(),),
            now=lambda: NOW,
            approved_keys=frozenset({"missing"}),
        )


@pytest.mark.asyncio
async def test_access_and_repeated_permanent_failures_override_baseline() -> None:
    access = ProviderStatusService(
        Reader((result(0, error="provider_auth_required"),)),
        (baseline(),),
        now=lambda: NOW,
    )
    blocked = ProviderStatusService(
        Reader(
            tuple(
                result(index, error="provider_content_restricted") for index in range(3)
            )
        ),
        (baseline(),),
        now=lambda: NOW,
    )

    assert (await access.list())[0].status is ProviderSupportStatus.ACCESS_REQUIRED
    assert (await blocked.list())[0].status is ProviderSupportStatus.BLOCKED


@pytest.mark.asyncio
async def test_wechat_channels_access_message_preserves_public_scope() -> None:
    wechat = replace(baseline(), key="wechat_channels")
    service = ProviderStatusService(
        Reader(
            (
                replace(
                    result(0, error="provider_auth_required"),
                    provider_key="wechat_channels",
                ),
            ),
            key="wechat_channels",
        ),
        (wechat,),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.user_action == (
        "公开分享链接需要部署已批准的隔离元宝会话；不支持私密、加密、直播或付费内容。"
    )


@pytest.mark.asyncio
async def test_failures_outside_the_recent_decision_window_do_not_degrade() -> None:
    service = ProviderStatusService(
        Reader(
            (
                *(result(index) for index in range(5)),
                result(6, error="inspection_timeout"),
                result(7, error="extractor_regression"),
            )
        ),
        (baseline(),),
        now=lambda: NOW,
    )

    assert (await service.list())[0].status is ProviderSupportStatus.UNKNOWN


@pytest.mark.asyncio
async def test_two_transient_failures_degrade_without_leaking_details() -> None:
    service = ProviderStatusService(
        Reader(
            (
                result(0, error="inspection_timeout"),
                result(1, error="extractor_regression"),
            )
        ),
        (baseline(),),
        now=lambda: NOW,
    )

    view = (await service.list())[0]

    assert view.status is ProviderSupportStatus.DEGRADED
    assert view.user_action == "平台当前不稳定，请稍后重试。"


@pytest.mark.asyncio
async def test_admin_catalog_controls_public_order_names_and_custom_entries() -> None:
    service = ProviderStatusService(
        Reader(()),
        (baseline(),),
        now=lambda: NOW,
        catalog=Catalog(),  # type: ignore[arg-type]
    )

    views = await service.list()

    assert [item.key for item in views] == ["custom", "vimeo"]
    assert views[0].status is ProviderSupportStatus.UNSUPPORTED
    assert views[0].registered is False
    assert views[1].display_name == "Vimeo 视频"
