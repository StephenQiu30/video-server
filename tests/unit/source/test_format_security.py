from __future__ import annotations

from typing import Any

import pytest

from video_server.errors import DomainError
from video_server.source.formats import normalize_formats


def _progressive(format_id: str, **overrides: Any) -> dict[str, Any]:
    raw = {
        "format_id": format_id,
        "ext": "mp4",
        "vcodec": "h264",
        "acodec": "aac",
        "width": 1280,
        "height": 720,
        "fps": 30,
        "dynamic_range": "SDR",
    }
    raw.update(overrides)
    return raw


@pytest.mark.parametrize(
    "drm_signal",
    [
        {"_has_drm": True},
        {"format_note": "DRM protected"},
        {"drm_families": ["widevine"]},
    ],
    ids=["yt-dlp-aggregate", "format-note", "drm-families"],
)
def test_any_drm_signal_rejects_the_entire_format_catalog(
    drm_signal: dict[str, Any],
) -> None:
    clear = _progressive("clear")
    protected = _progressive("protected", **drm_signal)

    with pytest.raises(DomainError) as caught:
        normalize_formats([clear, protected], "zh-CN")

    assert caught.value.code == "SOURCE_DRM_UNSUPPORTED"


def test_candidate_without_container_is_discarded() -> None:
    raw = _progressive("missing-container")
    del raw["ext"]

    assert normalize_formats([raw], "zh-CN") == []
