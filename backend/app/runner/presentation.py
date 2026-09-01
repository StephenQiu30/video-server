from __future__ import annotations

import hashlib

from app.domain.downloads import DownloadPlan
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
            _gallery_option(inspection)
            if inspection.media_kind.value == "image_gallery"
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


def _gallery_option(inspection: MediaInspection) -> list[DownloadOption]:
    return [
        DownloadOption(
            option_id="image-gallery-zip",
            label=f"下载 {inspection.asset_count} 张原图（ZIP）",
            media_kind=inspection.media_kind,
            asset_count=inspection.asset_count,
        )
    ]
