from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest
from app.domain.downloads import AudioCodecFamily, Container
from app.runner.errors import RunnerFailure
from app.runner.verification import verify_probe
from helpers import download_request


def probe() -> dict[str, object]:
    return {
        "format": {"format_name": "mov,mp4,m4a", "duration": "30"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }


def verify(payload: dict[str, object]) -> None:
    verify_probe(
        payload,
        plan=download_request().plan.to_domain(),
        expected_container=Container.MP4,
        expected_duration=30,
        max_duration=7200,
        tolerance_seconds=3,
    )


@pytest.mark.parametrize(
    "case",
    ["missing_audio", "container", "duration", "dimensions", "codec"],
)
def test_rejects_artifact_that_does_not_match_plan(case: str) -> None:
    payload = deepcopy(probe())
    format_info = payload["format"]
    streams = payload["streams"]
    assert isinstance(format_info, dict)
    assert isinstance(streams, list)
    video = streams[0]
    assert isinstance(video, dict)
    if case == "missing_audio":
        payload["streams"] = streams[:1]
    elif case == "container":
        format_info["format_name"] = "matroska,webm"
    elif case == "duration":
        format_info["duration"] = "40"
    elif case == "dimensions":
        video["height"] = 720
    else:
        video["codec_name"] = "vp9"

    with pytest.raises(RunnerFailure) as caught:
        verify(payload)

    assert caught.value.code == "media_validation_failed"


def test_accepts_a_silent_artifact_for_a_silent_plan() -> None:
    payload = probe()
    streams = payload["streams"]
    assert isinstance(streams, list)
    payload["streams"] = streams[:1]
    silent_plan = replace(
        download_request().plan.to_domain(),
        audio_codec_family=AudioCodecFamily.NONE,
        audio_language=None,
    )

    verified = verify_probe(
        payload,
        plan=silent_plan,
        expected_container=Container.MP4,
        expected_duration=30,
        max_duration=7200,
        tolerance_seconds=3,
    )

    assert verified.video_streams == 1
    assert verified.audio_streams == 0
