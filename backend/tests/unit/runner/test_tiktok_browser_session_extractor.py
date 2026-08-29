from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.tiktok_browser_session import (
    _TikTokBrowserSessionIE,
    _without_transport_impersonation,
)
from yt_dlp.extractor.tiktok import TikTokIE  # type: ignore[import-untyped]

VIDEO_ID = "7492902606063275294"
VIDEO_URL = f"https://www.tiktok.com/@nba/video/{VIDEO_ID}"
MEDIA_URL = "https://v16m.tiktokcdn.com/video.mp4?signature=redacted"


def player_payload() -> dict[str, Any]:
    return {
        "status_code": 0,
        "items": [
            {
                "id_str": VIDEO_ID,
                "desc": "Yuki is on fire",
                "author_info": {"nickname": "NBA", "unique_id": "nba"},
                "video_info": {
                    "meta": {"duration": 13_100, "width": 576, "height": 1024},
                    "cover": {"url_list": ["https://cdn.test/cover.jpg"]},
                    "profiles": [
                        {
                            "bitrate": 2_419_797,
                            "codec_type": "h264",
                            "fps": 30,
                            "play_addr": {
                                "data_size": 3_961_918,
                                "width": 576,
                                "height": 1024,
                                "url_list": [MEDIA_URL],
                            },
                        }
                    ],
                },
            }
        ],
    }


def test_webpage_request_drops_transport_impersonation() -> None:
    original = {"note": "Downloading webpage", "impersonate": True}

    assert _without_transport_impersonation(original) == {"note": "Downloading webpage"}
    assert original["impersonate"] is True


def test_plugin_registers_as_the_builtin_tiktok_override() -> None:
    assert _TikTokBrowserSessionIE.IE_NAME == "TikTok+browser_session"
    assert issubclass(_TikTokBrowserSessionIE, TikTokIE)
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

    assert "browser_session (TikTokIE)" in result.stderr
    assert str(backend_root / "app/runner/plugins/yt_dlp_plugins") in result.stderr


def test_uses_first_party_player_metadata_without_webpage_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TikTokBrowserSessionIE()
    requests: list[tuple[str, object]] = []

    def download_json(url: str, *_: object, **kwargs: object) -> object:
        requests.append((url, kwargs.get("query")))
        return player_payload()

    monkeypatch.setattr(extractor, "_download_json", download_json)

    info = extractor._real_extract(VIDEO_URL)

    assert info["id"] == VIDEO_ID
    assert info["duration"] == 13.1
    assert info["availability"] == "public"
    assert info["formats"][0]["url"] == MEDIA_URL
    assert info["formats"][0]["vcodec"] == "h264"
    assert info["formats"][0]["acodec"] == "aac"
    assert info["formats"][0]["http_headers"]["Referer"] == (
        f"https://www.tiktok.com/player/v1/{VIDEO_ID}"
    )
    assert requests == [
        (
            "https://www.tiktok.com/player/api/v1/items",
            {"item_ids": VIDEO_ID},
        )
    ]
