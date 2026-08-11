from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.kuaishou_public import (
    KuaishouPublicIE,
    _allowed_share_url,
    _state_photo,
    _video_formats,
)
from yt_dlp.utils import ExtractorError

VIDEO_ID = "3x888mrikrur4g2"
DESKTOP_URL = f"https://www.kuaishou.com/short-video/{VIDEO_ID}"
MOBILE_URL = f"https://v.m.chenzhongtech.com/fw/photo/{VIDEO_ID}"


def public_state(*, photo_type: str = "VIDEO") -> dict[str, Any]:
    return {
        "opaque-state-key": {
            "photo": {
                "photoType": photo_type,
                "share_info": f"userId=creator&photoId={VIDEO_ID}",
                "caption": "Public\nvideo",
                "duration": 72_533,
                "timestamp": 1_786_149_115_558,
                "userName": "Creator",
                "userEid": "creator",
                "width": 720,
                "height": 1280,
                "coverUrls": [{"url": "https://cdn.test/cover.jpg"}],
                "mainMvUrls": [{"url": "https://cdn.test/source.mp4"}],
                "manifest": {
                    "adaptationSet": [
                        {
                            "representation": [
                                {
                                    "id": 1,
                                    "url": "https://cdn.test/avc.mp4",
                                    "videoCodec": "avc",
                                    "qualityType": "720p",
                                    "qualityLabel": "高清",
                                    "width": 720,
                                    "height": 1280,
                                    "frameRate": 30,
                                    "avgBitrate": 1803,
                                    "fileSize": 16_359_245,
                                },
                                {
                                    "id": 2,
                                    "backupUrl": ["https://cdn.test/hevc.mp4"],
                                    "videoCodec": "hevc",
                                    "qualityType": "720p",
                                    "width": 720,
                                    "height": 1280,
                                },
                            ]
                        }
                    ]
                },
            }
        }
    }


def configured_extractor(
    monkeypatch: pytest.MonkeyPatch,
    state: object,
    *,
    final_url: str = MOBILE_URL,
) -> KuaishouPublicIE:
    extractor = KuaishouPublicIE()
    monkeypatch.setattr(
        extractor,
        "_download_webpage_handle",
        lambda *args, **kwargs: ("initial state", SimpleNamespace(url=final_url)),
    )
    monkeypatch.setattr(extractor, "_search_json", lambda *args, **kwargs: state)
    return extractor


def test_extracts_verified_public_video_formats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = configured_extractor(monkeypatch, public_state())

    info = extractor._real_extract(DESKTOP_URL)

    assert info["id"] == VIDEO_ID
    assert info["title"] == "Public video"
    assert info["duration"] == 72.533
    assert info["timestamp"] == 1_786_149_115.558
    assert info["thumbnail"] == "https://cdn.test/cover.jpg"
    assert [item["format_id"] for item in info["formats"]] == [
        "h264-720p-1",
        "hevc-720p-2",
    ]
    assert info["formats"][0]["acodec"] == "aac"
    assert info["formats"][1]["url"] == "https://cdn.test/hevc.mp4"


def test_uses_first_party_mobile_page_for_desktop_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = KuaishouPublicIE()
    requests: list[str] = []

    def download(url: str, *args: object, **kwargs: object) -> object:
        requests.append(url)
        return "state", SimpleNamespace(url=MOBILE_URL)

    monkeypatch.setattr(extractor, "_download_webpage_handle", download)
    monkeypatch.setattr(
        extractor, "_search_json", lambda *args, **kwargs: public_state()
    )

    extractor._real_extract(DESKTOP_URL)

    assert requests == [MOBILE_URL]


def test_rejects_identity_mismatch_and_non_video_posts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mismatched = public_state()
    mismatched["opaque-state-key"]["photo"]["share_info"] = "photoId=other"
    with pytest.raises(ExtractorError, match="public link unavailable"):
        configured_extractor(monkeypatch, mismatched)._real_extract(DESKTOP_URL)

    with pytest.raises(ExtractorError, match="image posts are not supported"):
        configured_extractor(
            monkeypatch, public_state(photo_type="VERTICAL_ATLAS")
        )._real_extract(DESKTOP_URL)


def test_short_link_redirect_is_limited_to_first_party_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = configured_extractor(
        monkeypatch,
        public_state(),
        final_url=f"https://media.example/fw/photo/{VIDEO_ID}",
    )

    with pytest.raises(ExtractorError, match="public link unavailable"):
        extractor._real_extract("https://v.kuaishou.com/8qIlZu")

    assert _allowed_share_url("https://c.kuaishou.com/fw/photo/example")
    assert _allowed_share_url("https://sub.m.chenzhongtech.com/fw/photo/example")
    assert not _allowed_share_url("https://kuaishou.com.example/fw/photo/example")


def test_matches_first_party_mobile_share_subdomains() -> None:
    assert KuaishouPublicIE.suitable(f"https://c.kuaishou.com/fw/photo/{VIDEO_ID}")


def test_format_fallback_and_state_identity() -> None:
    state = public_state()
    photo = state["opaque-state-key"]["photo"]
    photo["manifest"] = {}

    assert _state_photo(state, VIDEO_ID) is photo
    assert _state_photo(state, "other") is None
    assert _video_formats(photo)[0]["format_id"] == "h264-source"


def test_plugin_registers_with_ytdlp() -> None:
    backend_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            str(Path(sys.executable).with_name("yt-dlp")),
            "--ignore-config",
            "--verbose",
            "--plugin-dirs",
            str(backend_root / "app/runner"),
            "--simulate",
            "--",
            "file:///disabled",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert "KuaishouPublic" in result.stderr
    assert str(backend_root / "app/runner/plugins/yt_dlp_plugins") in result.stderr
