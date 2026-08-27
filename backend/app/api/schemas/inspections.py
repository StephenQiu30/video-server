from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.schemas.common import StrictModel
from app.application.downloads import InspectionView
from app.domain.downloads import (
    AccessDecision,
    AudioCodecFamily,
    CompatibilityProfile,
    ContainerPreference,
    DynamicRange,
    EntitlementState,
    ExecutionMode,
    FpsBucket,
    IdentityState,
    ProtectionState,
    RightsBasis,
    SourceOrigin,
    VideoCodecFamily,
)


class InspectionRequest(StrictModel):
    """Public media URL submitted for safe metadata inspection."""

    url: str = Field(
        description="用户有权处理的公开、非 DRM HTTP(S) 媒体地址。",
        examples=["https://media.example/video"],
        min_length=8,
        max_length=4096,
    )


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
    """Inspection resource with normalized semantic download formats."""

    id: UUID
    extractor_key: str
    provider_media_id: str
    title: str
    duration_seconds: int
    thumbnail_url: str | None
    expires_at: datetime
    formats: tuple[FormatResponse, ...]
    source_origin: SourceOrigin
    execution_mode: ExecutionMode
    access_decision: AccessDecision
    entitlement_state: EntitlementState
    identity_state: IdentityState
    protection_state: ProtectionState
    rights_basis: RightsBasis | None
    restriction_reason: str | None
    user_action: str | None

    @classmethod
    def from_view(cls, view: InspectionView) -> InspectionResponse:
        return cls(
            id=view.id,
            extractor_key=view.extractor_key,
            provider_media_id=view.provider_media_id,
            title=view.title,
            duration_seconds=view.duration_seconds,
            thumbnail_url=view.thumbnail_url,
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
            source_origin=view.source_origin,
            execution_mode=view.execution_mode,
            access_decision=view.access_decision,
            entitlement_state=view.entitlement_state,
            identity_state=view.identity_state,
            protection_state=view.protection_state,
            rights_basis=view.rights_basis,
            restriction_reason=view.restriction_reason,
            user_action=view.user_action,
        )
