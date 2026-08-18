from __future__ import annotations

from dataclasses import dataclass
from math import log

from app.application.downloads.inspection_models import FormatView
from app.application.downloads.plans import plan_from_documents, plan_to_documents
from app.domain.downloads import (
    ContainerPreference,
    DownloadPlan,
    VideoCodecFamily,
)

_MP4_VIDEO_CODECS = frozenset({VideoCodecFamily.H264, VideoCodecFamily.HEVC})
_WEBM_VIDEO_CODECS = frozenset({VideoCodecFamily.VP9, VideoCodecFamily.AV1})


@dataclass(frozen=True, slots=True)
class RetryFormatResolution:
    selected: FormatView
    adapted: bool


class RetryFormatRecoveryPolicy:
    """Resolve a stale semantic selection against one fresh inspection.

    An exact semantic match always wins. A fallback remains inside the same
    container family, aspect ratio, frame-rate, dynamic-range and audio
    contract. It is used only after an explicit retry action, so a provider
    rendition disappearing does not force the user through another format
    picker while the new job still records the format it will actually fetch.
    """

    def resolve(
        self,
        requested_semantic: dict[str, object],
        available: tuple[FormatView, ...],
    ) -> RetryFormatResolution | None:
        exact = next(
            (
                item
                for item in available
                if plan_to_documents(item.plan)[0] == requested_semantic
            ),
            None,
        )
        if exact is not None:
            return RetryFormatResolution(exact, adapted=False)
        try:
            requested = plan_from_documents(requested_semantic, {})
        except (TypeError, ValueError):
            return None
        compatible = tuple(
            item for item in available if _compatible(requested, item.plan)
        )
        if not compatible:
            return None
        selected = min(compatible, key=lambda item: _rank(requested, item.plan))
        return RetryFormatResolution(selected, adapted=True)


def _compatible(requested: DownloadPlan, candidate: DownloadPlan) -> bool:
    if (
        candidate.container_preference is not requested.container_preference
        or candidate.dynamic_range is not requested.dynamic_range
        or candidate.fps_bucket is not requested.fps_bucket
        or candidate.audio_codec_family is not requested.audio_codec_family
        or (
            requested.audio_language is not None
            and candidate.audio_language != requested.audio_language
        )
        or candidate.video_codec_family
        not in _compatible_video_codecs(
            requested.container_preference,
            requested.video_codec_family,
        )
    ):
        return False
    requested_ratio = requested.width / requested.height
    candidate_ratio = candidate.width / candidate.height
    return abs(candidate_ratio - requested_ratio) / requested_ratio <= 0.03


def _compatible_video_codecs(
    container: ContainerPreference,
    requested: VideoCodecFamily,
) -> frozenset[VideoCodecFamily]:
    if container is ContainerPreference.MP4:
        return _MP4_VIDEO_CODECS
    if container is ContainerPreference.WEBM:
        return _WEBM_VIDEO_CODECS
    # A SOURCE plan does not promise a remuxable output family. Keep its
    # original codec instead of silently crossing arbitrary container bounds.
    return frozenset({requested})


def _rank(requested: DownloadPlan, candidate: DownloadPlan) -> tuple[int, float, int]:
    requested_area = requested.width * requested.height
    candidate_area = candidate.width * candidate.height
    codec_changed = int(
        candidate.video_codec_family is not requested.video_codec_family
    )
    area_distance = abs(log(candidate_area / requested_area))
    # Prefer the higher rendition when two candidates are equally close.
    return codec_changed, area_distance, -candidate_area
