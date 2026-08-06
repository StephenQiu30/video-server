from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.v1.schemas.common import StrictModel
from app.application.downloads import InspectionView
from app.domain.downloads import (
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DynamicRange,
    FpsBucket,
    VideoCodecFamily,
)


class InspectionRequest(StrictModel):
    url: str = Field(min_length=8, max_length=4096)


class SemanticPlanResponse(StrictModel):
    height: int
    width: int
    fps_bucket: FpsBucket
    dynamic_range: DynamicRange
    video_codec_family: VideoCodecFamily
    audio_codec_family: AudioCodecFamily
    audio_language: str | None
    container_preference: ContainerPreference
    compatibility_profile: CompatibilityProfile


class FormatResponse(StrictModel):
    id: UUID
    display_name: str
    plan: SemanticPlanResponse


class InspectionResponse(StrictModel):
    id: UUID
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    expires_at: datetime
    formats: tuple[FormatResponse, ...]

    @classmethod
    def from_view(cls, view: InspectionView) -> InspectionResponse:
        return cls(
            id=view.id,
            extractor_key=view.extractor_key,
            provider_media_id=view.provider_media_id,
            title=view.title,
            duration_seconds=view.duration_seconds,
            expires_at=view.expires_at,
            formats=tuple(
                FormatResponse(
                    id=item.id,
                    display_name=item.display_name,
                    plan=SemanticPlanResponse(
                        height=item.plan.height,
                        width=item.plan.width,
                        fps_bucket=item.plan.fps_bucket,
                        dynamic_range=item.plan.dynamic_range,
                        video_codec_family=item.plan.video_codec_family,
                        audio_codec_family=item.plan.audio_codec_family,
                        audio_language=item.plan.audio_language,
                        container_preference=item.plan.container_preference,
                        compatibility_profile=item.plan.compatibility_profile,
                    ),
                )
                for item in view.formats
            ),
        )
