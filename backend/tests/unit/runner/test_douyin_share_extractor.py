from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.douyin_share import (
    _correct_download_addr_dimensions,
    _DouyinSharePageIE,
    _router_item,
)
from yt_dlp.extractor.tiktok import DouyinIE

VIDEO_ID = "7662711608636889201"
URL = f"https://www.douyin.com/video/{VIDEO_ID}"


def router_payload(video_id: str = VIDEO_ID) -> dict[str, Any]:
    return {
        "loaderData": {
            "video_(id)/page": {
                "videoInfoRes": {
                    "item_list": [
                        {
                            "aweme_id": video_id,
                            "desc": "Public video",
                            "video": {
                                "bit_rate": None,
                                "play_addr": {"url_list": ["https://cdn.test/video"]},
                            },
                        }
                    ]
                }
            }
        }
    }


def test_prefers_matching_public_share_page_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _DouyinSharePageIE()
    requests: list[tuple[str, str, dict[str, object]]] = []

    def download_webpage(
        url: str,
        video_id: str,
        **kwargs: object,
    ) -> str:
        requests.append((url, video_id, kwargs))
        return "router data"

    monkeypatch.setattr(extractor, "_download_webpage", download_webpage)
    monkeypatch.setattr(
        extractor,
        "_search_json",
        lambda *args, **kwargs: router_payload(),
    )
    monkeypatch.setattr(
        extractor,
        "_parse_aweme_video_app",
        lambda item: {
            "id": item["aweme_id"],
            "title": "Public\nvideo",
            "formats": [{"url": "https://cdn.test/video"}],
        },
    )

    info = extractor._real_extract(URL)

    assert info == {
        "id": VIDEO_ID,
        "title": "Public video",
        "formats": [{"url": "https://cdn.test/video"}],
    }
    assert requests[0][0] == f"https://www.iesdouyin.com/share/video/{VIDEO_ID}/"
    assert requests[0][1] == VIDEO_ID
    assert requests[0][2]["fatal"] is False


def test_corrects_download_format_dimensions_from_video_source() -> None:
    info = _correct_download_addr_dimensions(
        {
            "formats": [
                {"format_id": "download_addr-0", "width": 720, "height": 405},
                {"format_id": "h264_540p-0", "width": 1024, "height": 576},
            ]
        },
        {"video": {"width": 3840, "height": 2160}},
    )

    assert info["formats"] == [
        {"format_id": "download_addr-0", "width": 1280, "height": 720},
        {"format_id": "h264_540p-0", "width": 1024, "height": 576},
    ]


def test_keeps_upstream_download_dimensions_for_portrait_video() -> None:
    info = _correct_download_addr_dimensions(
        {"formats": [{"format_id": "download_addr-0", "width": 720, "height": 1280}]},
        {"video": {"width": 2160, "height": 3840}},
    )

    assert info["formats"] == [
        {"format_id": "download_addr-0", "width": 720, "height": 1280}
    ]


def test_falls_back_to_upstream_extractor_without_share_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _DouyinSharePageIE()
    monkeypatch.setattr(extractor, "_download_webpage", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        DouyinIE,
        "_real_extract",
        lambda self, url: {"id": VIDEO_ID, "source": "upstream"},
    )

    assert extractor._real_extract(URL) == {"id": VIDEO_ID, "source": "upstream"}


@pytest.mark.parametrize(
    "item",
    [
        {"aweme_id": VIDEO_ID},
        {"aweme_id": VIDEO_ID, "video": {}},
        {"aweme_id": VIDEO_ID, "video": {"play_addr": "invalid"}},
    ],
)
def test_falls_back_when_matching_share_item_is_not_playable(
    monkeypatch: pytest.MonkeyPatch,
    item: dict[str, object],
) -> None:
    extractor = _DouyinSharePageIE()
    payload = {
        "loaderData": {
            "video_(id)/page": {
                "videoInfoRes": {"item_list": [item]},
            }
        }
    }
    monkeypatch.setattr(extractor, "_download_webpage", lambda *args, **kwargs: "data")
    monkeypatch.setattr(extractor, "_search_json", lambda *args, **kwargs: payload)
    monkeypatch.setattr(
        DouyinIE,
        "_real_extract",
        lambda self, url: {"id": VIDEO_ID, "source": "upstream"},
    )

    assert extractor._real_extract(URL) == {"id": VIDEO_ID, "source": "upstream"}


def test_router_item_requires_the_requested_video_identity() -> None:
    payload = router_payload()
    item = _router_item(payload, VIDEO_ID)

    assert item is not None
    assert item["video"]["bit_rate"] == []
    original = payload["loaderData"]["video_(id)/page"]["videoInfoRes"]["item_list"][0]
    assert original["video"]["bit_rate"] is None
    assert _router_item(router_payload("1234567890123456789"), VIDEO_ID) is None
    assert _router_item({"loaderData": []}, VIDEO_ID) is None


def test_plugin_registers_as_the_builtin_douyin_override() -> None:
    assert _DouyinSharePageIE.IE_NAME == "Douyin+share_page"
    assert issubclass(_DouyinSharePageIE, DouyinIE)
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

    assert "share_page (DouyinIE)" in result.stderr
    assert str(backend_root / "app/runner/plugins/yt_dlp_plugins") in result.stderr
