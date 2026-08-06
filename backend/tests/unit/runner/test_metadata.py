from __future__ import annotations

from copy import deepcopy

import pytest
from app.domain.downloads import (
    AudioCodecFamily,
    Container,
    StreamKind,
    VideoCodecFamily,
)
from app.runner.errors import RunnerFailure
from app.runner.metadata import (
    build_download_options,
    enrich_direct_metadata,
    enrich_format_metadata,
    normalize_metadata,
)


def media_info() -> dict[str, object]:
    return {
        "id": "controlled-video",
        "title": "Controlled fixture",
        "duration": 60.5,
        "extractor_key": "Controlled",
        "webpage_url_domain": "media.example.com",
        "live_status": "not_live",
        "formats": [
            {
                "format_id": "muxed-1080",
                "ext": "mp4",
                "width": 1920,
                "height": 1080,
                "fps": 29.97,
                "vcodec": "avc1.640028",
                "acodec": "mp4a.40.2",
                "language": "zh-CN",
                "tbr": 2500,
                "filesize": 20_000_000,
            },
            {
                "format_id": "video-720",
                "ext": "webm",
                "width": 1280,
                "height": 720,
                "fps": 60,
                "vcodec": "vp09.00.40.08",
                "acodec": "none",
            },
            {
                "format_id": "audio-opus",
                "ext": "webm",
                "vcodec": "none",
                "acodec": "opus",
                "language": "en",
                "abr": 128,
            },
        ],
    }


def test_normalizes_ytdlp_formats_into_domain_streams_and_options() -> None:
    payload = media_info()
    payload["thumbnail"] = "https://images.example.com/cover.webp"
    inspection = normalize_metadata(
        payload,
        max_duration_seconds=7200,
        max_candidate_streams=200,
    )

    assert inspection.title == "Controlled fixture"
    assert inspection.provider_media_id == "controlled-video"
    assert inspection.extractor_key == "Controlled"
    assert inspection.duration_seconds == 60.5
    assert inspection.thumbnail_url == "https://images.example.com/cover.webp"
    assert len(inspection.streams) == 3
    muxed, video, audio = inspection.streams
    assert muxed.kind is StreamKind.MUXED
    assert muxed.container is Container.MP4
    assert muxed.video_codec_family is VideoCodecFamily.H264
    assert muxed.audio_codec_family is AudioCodecFamily.AAC
    assert video.kind is StreamKind.VIDEO
    assert video.video_codec_family is VideoCodecFamily.VP9
    assert audio.kind is StreamKind.AUDIO
    assert audio.audio_codec_family is AudioCodecFamily.OPUS

    options = build_download_options(inspection.streams, max_options=20)
    assert {(item.height, item.container_preference.value) for item in options} == {
        (1080, "mp4"),
        (720, "webm"),
    }


def test_ignores_unsafe_thumbnail_urls() -> None:
    payload = media_info()
    payload["thumbnail"] = "http://127.0.0.1/private-cover"

    inspection = normalize_metadata(
        payload,
        max_duration_seconds=7200,
        max_candidate_streams=200,
    )

    assert inspection.thumbnail_url is None


def test_enriches_sparse_direct_media_with_ffprobe_metadata() -> None:
    payload = {
        "id": "sample",
        "title": "sample",
        "extractor_key": "Generic",
        "direct": True,
        "formats": [{"format_id": "mp4", "ext": "mp4"}],
    }
    probe = {
        "format": {"duration": "3.704", "size": "409785", "bit_rate": "885064"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 640,
                "height": 360,
                "avg_frame_rate": "30/1",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"language": "und"},
            },
        ],
    }

    inspection = normalize_metadata(
        enrich_direct_metadata(payload, probe),
        max_duration_seconds=7200,
        max_candidate_streams=200,
    )

    assert inspection.duration_seconds == 3.704
    assert inspection.streams[0].kind is StreamKind.MUXED
    assert inspection.streams[0].height == 360
    assert inspection.streams[0].fps == 30


def test_enriches_single_sparse_provider_format_with_ffprobe_metadata() -> None:
    raw = {
        "format_id": "http-832",
        "ext": "mp4",
        "url": "https://cdn.example.com/video.mp4",
    }
    probe = {
        "format": {"size": "409785", "bit_rate": "885064"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 640,
                "height": 360,
                "avg_frame_rate": "30000/1001",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"language": "en"},
            },
        ],
    }

    enriched = enrich_format_metadata(raw, probe)

    assert enriched["vcodec"] == "h264"
    assert enriched["acodec"] == "aac"
    assert enriched["width"] == 640
    assert enriched["height"] == 360
    assert enriched["fps"] == pytest.approx(29.97, rel=0.001)
    assert enriched["dynamic_range"] == "SDR"
    assert enriched["language"] == "en"
    assert enriched["filesize"] == "409785"
    assert enriched["tbr"] == pytest.approx(885.064)


def test_ignores_sub_unit_provider_metrics_after_integer_normalization() -> None:
    payload = media_info()
    formats = payload["formats"]
    assert isinstance(formats, list)
    first = formats[0]
    assert isinstance(first, dict)
    first["tbr"] = 0.248

    inspection = normalize_metadata(
        payload,
        max_duration_seconds=7200,
        max_candidate_streams=200,
    )

    assert inspection.streams[0].bitrate_kbps is None


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"_type": "playlist", "entries": []}, "unsupported_source"),
        ({"is_live": True}, "unsupported_source"),
        ({"live_status": "is_upcoming"}, "unsupported_source"),
        ({"has_drm": True}, "unsupported_source"),
        ({"duration": 7201}, "duration_limit_exceeded"),
        ({"duration": None}, "unsupported_source"),
    ],
)
def test_rejects_unsupported_media_metadata(
    change: dict[str, object],
    code: str,
) -> None:
    payload = deepcopy(media_info())
    payload.update(change)

    with pytest.raises(RunnerFailure) as caught:
        normalize_metadata(
            payload,
            max_duration_seconds=7200,
            max_candidate_streams=200,
        )

    assert caught.value.code == code


@pytest.mark.parametrize(
    "provider_id",
    ["x" * 129, "video\n1080", "video\n", "video+audio", "-video"],
)
def test_rejects_unsafe_provider_format_identifier(provider_id: str) -> None:
    payload = media_info()
    formats = payload["formats"]
    assert isinstance(formats, list)
    first = formats[0]
    assert isinstance(first, dict)
    first["format_id"] = provider_id

    with pytest.raises(RunnerFailure) as caught:
        normalize_metadata(
            payload,
            max_duration_seconds=7200,
            max_candidate_streams=200,
        )

    assert caught.value.code == "invalid_inspection_response"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "x" * 257),
        ("id", "media\nidentity"),
        ("extractor_key", "x" * 129),
        ("extractor_key", "Controlled\x7f"),
    ],
)
def test_rejects_unsafe_media_identity(field: str, value: str) -> None:
    payload = media_info()
    payload[field] = value

    with pytest.raises(RunnerFailure) as caught:
        normalize_metadata(
            payload,
            max_duration_seconds=7200,
            max_candidate_streams=200,
        )

    assert caught.value.code == "invalid_inspection_response"
