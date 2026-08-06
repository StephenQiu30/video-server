from __future__ import annotations

from dataclasses import replace

from app.domain.downloads import (
    CandidateStream,
    CompatibilityProfile,
    ContainerPreference,
    DownloadPlan,
    FormatSelectionError,
    FpsBucket,
    ProviderHints,
    StreamKind,
    select_streams,
)


def build_download_options(
    streams: tuple[CandidateStream, ...],
    *,
    max_options: int,
) -> tuple[DownloadPlan, ...]:
    proposed: dict[tuple[object, ...], DownloadPlan] = {}
    muxed = [stream for stream in streams if stream.kind is StreamKind.MUXED]
    videos = [stream for stream in streams if stream.kind is StreamKind.VIDEO]
    audios = [stream for stream in streams if stream.kind is StreamKind.AUDIO]

    for stream in muxed:
        for container in (ContainerPreference.MP4, ContainerPreference.WEBM):
            plan = _plan(stream, stream, container)
            if plan is not None:
                _add_viable(proposed, plan, streams)
    for video in videos:
        for audio in audios:
            for container in (ContainerPreference.MP4, ContainerPreference.WEBM):
                plan = _plan(video, audio, container)
                if plan is not None:
                    _add_viable(proposed, plan, streams)

    ordered = sorted(
        proposed.values(),
        key=lambda item: (
            -item.height,
            -item.width,
            item.container_preference.value,
            item.video_codec_family.value,
            item.audio_codec_family.value,
            item.audio_language or "",
        ),
    )
    return tuple(ordered[:max_options])


def _plan(
    video: CandidateStream,
    audio: CandidateStream,
    container: ContainerPreference,
) -> DownloadPlan | None:
    required = (
        video.height,
        video.width,
        video.fps,
        video.dynamic_range,
        video.video_codec_family,
        audio.audio_codec_family,
    )
    if any(value is None for value in required):
        return None
    assert video.height is not None
    assert video.width is not None
    assert video.fps is not None
    assert video.dynamic_range is not None
    assert video.video_codec_family is not None
    assert audio.audio_codec_family is not None
    return DownloadPlan(
        height=video.height,
        width=video.width,
        fps_bucket=FpsBucket.from_fps(video.fps),
        dynamic_range=video.dynamic_range,
        video_codec_family=video.video_codec_family,
        audio_codec_family=audio.audio_codec_family,
        audio_language=audio.audio_language,
        container_preference=container,
        compatibility_profile=CompatibilityProfile.BALANCED,
        hints=ProviderHints(
            video_id=video.provider_id,
            audio_id=None if video is audio else audio.provider_id,
        ),
    )


def _add_viable(
    options: dict[tuple[object, ...], DownloadPlan],
    plan: DownloadPlan,
    streams: tuple[CandidateStream, ...],
) -> None:
    try:
        selection = select_streams(plan, streams)
    except FormatSelectionError:
        return
    resolved = replace(
        plan,
        hints=ProviderHints(
            video_id=selection.video.provider_id,
            audio_id=(
                selection.audio.provider_id if selection.audio is not None else None
            ),
        ),
    )
    key = (
        resolved.height,
        resolved.width,
        resolved.fps_bucket,
        resolved.dynamic_range,
        resolved.video_codec_family,
        resolved.audio_codec_family,
        resolved.audio_language,
        resolved.container_preference,
        resolved.compatibility_profile,
    )
    options.setdefault(key, resolved)
