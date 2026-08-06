from __future__ import annotations

import hashlib

from app.domain.downloads import DownloadPlan
from app.runner.contracts import (
    CandidateStreamContract,
    DownloadOption,
    DownloadPlanContract,
    InspectResponse,
    MediaSummary,
)
from app.runner.metadata import MediaInspection


def inspect_response(
    inspection: MediaInspection,
    plans: tuple[DownloadPlan, ...],
    *,
    thumbnail_data_url: str | None = None,
) -> InspectResponse:
    return InspectResponse(
        media=MediaSummary(
            provider_media_id=inspection.provider_media_id,
            title=inspection.title,
            duration_seconds=inspection.duration_seconds,
            extractor_key=inspection.extractor_key,
            thumbnail_data_url=thumbnail_data_url,
        ),
        streams=[
            CandidateStreamContract.from_domain(stream) for stream in inspection.streams
        ],
        options=[_option(plan) for plan in plans],
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
