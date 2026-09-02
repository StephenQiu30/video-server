from __future__ import annotations

import hashlib

from app.domain.downloads import DownloadPlan, MediaKind
from app.domain.providers import ProviderAccessContextRef
from app.runner.contracts import (
    CandidateStreamContract,
    DownloadOption,
    DownloadPlanContract,
    InspectResponse,
    MediaSummary,
    ProviderAccessContextContract,
)
from app.runner.metadata import MediaInspection


def inspect_response(
    inspection: MediaInspection,
    plans: tuple[DownloadPlan, ...],
    *,
    access_context: ProviderAccessContextRef,
    thumbnail_data_url: str | None = None,
) -> InspectResponse:
    return InspectResponse(
        media=MediaSummary(
            provider_media_id=inspection.provider_media_id,
            title=inspection.title,
            duration_seconds=inspection.duration_seconds,
            extractor_key=inspection.extractor_key,
            thumbnail_data_url=thumbnail_data_url,
            media_kind=inspection.media_kind,
            asset_count=inspection.asset_count,
        ),
        streams=[
            CandidateStreamContract.from_domain(stream) for stream in inspection.streams
        ],
        options=(
            _archive_option(inspection)
            if inspection.media_kind
            in {MediaKind.IMAGE_GALLERY, MediaKind.VIDEO_COLLECTION}
            else [_option(plan) for plan in plans]
        ),
        access_context=ProviderAccessContextContract.from_domain(access_context),
    )


def _option(plan: DownloadPlan) -> DownloadOption:
    contract = DownloadPlanContract.from_domain(plan)
    semantic = contract.model_dump_json(exclude={"hints"})
    digest = hashlib.sha256(semantic.encode()).hexdigest()[:16]
    label = (
        f"{plan.height}p · {plan.container_preference.value.upper()} · "
        f"{plan.video_codec_family.value.upper()}/"
        f"{plan.audio_codec_family.value.upper()}"
    )
    return DownloadOption(option_id=digest, label=label, plan=contract)


def _archive_option(inspection: MediaInspection) -> list[DownloadOption]:
    unit = "张原图" if inspection.media_kind is MediaKind.IMAGE_GALLERY else "个视频"
    option_id = (
        "image-gallery-zip"
        if inspection.media_kind is MediaKind.IMAGE_GALLERY
        else "video-collection-zip"
    )
    return [
        DownloadOption(
            option_id=option_id,
            label=f"下载 {inspection.asset_count} {unit}（ZIP）",
            media_kind=inspection.media_kind,
            asset_count=inspection.asset_count,
        )
    ]
