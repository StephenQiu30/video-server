from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.tiktok_public_player import (
    _TikTokPublicPlayerIE,
    _TikTokPublicShortIE,
)
from yt_dlp.extractor.tiktok import TikTokIE  # type: ignore[import-untyped]
from yt_dlp.networking.exceptions import (  # type: ignore[import-untyped]
    TransportError,
)
from yt_dlp.utils import ExtractorError  # type: ignore[import-untyped]

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


def test_plugin_registers_as_the_builtin_tiktok_override() -> None:
    assert _TikTokPublicPlayerIE.IE_NAME == "TikTok+public_player"
    assert issubclass(_TikTokPublicPlayerIE, TikTokIE)
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

    assert "public_player (TikTokIE)" in result.stderr
    assert "public_short (TikTokVMIE)" in result.stderr
    assert str(backend_root / "app/runner/plugins/yt_dlp_plugins") in result.stderr


def test_uses_first_party_player_metadata_without_webpage_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TikTokPublicPlayerIE()
    requests: list[tuple[str, dict[str, object]]] = []

    def download_json(url: str, *_: object, **kwargs: object) -> object:
        requests.append((url, kwargs))
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
    assert len(requests) == 1
    assert requests[0][0] == "https://www.tiktok.com/player/api/v1/items"
    request = requests[0][1]
    assert request["query"] == {"item_ids": VIDEO_ID}
    assert request["headers"] == {
        "Referer": f"https://www.tiktok.com/player/v1/{VIDEO_ID}"
    }
    assert "fatal" not in request
    assert "impersonate" not in request
    assert "cookies" not in request


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        (None, "TikTok official player response structure changed"),
        ({"status_code": "0", "items": []}, "response structure changed"),
        ({"status_code": 0}, "response structure changed"),
        (
            {
                "status_code": 0,
                "results": [{"code": "nil_core_data", "id": 123, "id_str": VIDEO_ID}],
            },
            "TikTok video not available from the official player",
        ),
        (
            {
                "status_code": 0,
                "results": [{"code": "api_busy", "id_str": VIDEO_ID}],
            },
            "TikTok official player API temporarily unavailable",
        ),
        (
            {
                "status_code": 0,
                "results": [{"code": "ok", "id_str": VIDEO_ID}],
            },
            "response structure changed",
        ),
        (
            {"status_code": 0, "items": [{"id_str": "987654321"}]},
            "response structure changed",
        ),
        (
            {"status_code": 1, "status_msg": "Service unavailable", "items": None},
            "TikTok official player API temporarily unavailable",
        ),
        (
            {"status_code": 5, "status_msg": "Invalid parameters", "items": None},
            "TikTok video not available from the official player",
        ),
        (
            {"status_code": 0, "items": None},
            "TikTok video not available from the official player",
        ),
        (
            {
                "status_code": 0,
                "items": None,
                "results": [{"code": "api_busy", "id_str": VIDEO_ID}],
            },
            "TikTok official player API temporarily unavailable",
        ),
        (
            {
                "status_code": 0,
                "items": None,
                "results": [{"code": "ok", "id_str": VIDEO_ID}],
            },
            "response structure changed",
        ),
        (
            {"status_code": 0, "items": []},
            "TikTok video not available from the official player",
        ),
        (
            {
                "status_code": 0,
                "items": [{"id_str": VIDEO_ID, "video_info": {"profiles": {}}}],
            },
            "response structure changed",
        ),
        (
            {
                "status_code": 0,
                "items": [
                    {
                        "id_str": VIDEO_ID,
                        "video_info": {
                            "profiles": [
                                {
                                    "play_addr": {
                                        "url_list": ["http://cdn.test/video.mp4"]
                                    }
                                }
                            ]
                        },
                    }
                ],
            },
            "TikTok video not available from the official player",
        ),
    ),
)
def test_player_response_facts_have_distinct_stable_failures_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
    message: str,
) -> None:
    extractor = _TikTokPublicPlayerIE()
    fallback_calls: list[str] = []

    def upstream_fallback(_extractor: object, url: str) -> dict[str, object]:
        fallback_calls.append(url)
        return {"id": VIDEO_ID}

    monkeypatch.setattr(extractor, "_download_json", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(
        _TikTokPublicPlayerIE.__mro__[1],
        "_real_extract",
        upstream_fallback,
    )

    with pytest.raises(
        ExtractorError,
        match=message,
    ) as captured:
        extractor._real_extract(VIDEO_URL)

    assert captured.value.expected is True
    assert fallback_calls == []


def test_player_transport_failure_is_not_folded_into_missing_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TikTokPublicPlayerIE()

    def fail_transport(*_args: object, **_kwargs: object) -> object:
        raise ExtractorError(
            "Unable to download JSON metadata",
            cause=TransportError("connection reset"),
        )

    monkeypatch.setattr(extractor, "_download_json", fail_transport)

    with pytest.raises(
        ExtractorError,
        match="TikTok official player API temporarily unavailable",
    ) as captured:
        extractor._real_extract(VIDEO_URL)

    assert captured.value.expected is True


def test_invalid_player_json_is_an_extractor_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TikTokPublicPlayerIE()

    def fail_json(*_args: object, **_kwargs: object) -> object:
        raise ExtractorError("Failed to parse JSON", cause=ValueError("invalid JSON"))

    monkeypatch.setattr(extractor, "_download_json", fail_json)

    with pytest.raises(
        ExtractorError,
        match="TikTok official player response structure changed",
    ) as captured:
        extractor._real_extract(VIDEO_URL)

    assert captured.value.expected is True


@pytest.mark.parametrize(
    ("redirected", "expected"),
    (
        (
            "https://www.tiktok.com/@creator/video/7492902606063275294?share=1",
            "https://www.tiktok.com/@creator/video/7492902606063275294",
        ),
        (
            "https://www.tiktok.com/embed/7492902606063275294",
            "https://www.tiktok.com/embed/7492902606063275294",
        ),
    ),
)
def test_short_link_resolves_only_to_public_player_urls(
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
    expected: str,
) -> None:
    extractor = _TikTokPublicShortIE()
    response = type("Response", (), {"url": redirected})()
    requests: list[dict[str, object]] = []

    def request_webpage(*_args: object, **kwargs: object) -> object:
        requests.append(kwargs)
        return response

    monkeypatch.setattr(
        extractor,
        "_request_webpage",
        request_webpage,
    )

    result = extractor._real_extract("https://vm.tiktok.com/ZTR45GpSF")

    assert result["url"] == expected
    assert result["ie_key"] == _TikTokPublicPlayerIE.ie_key()
    assert requests == [{"note": "Resolving TikTok public video link"}]


def test_short_link_transport_failure_is_temporary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TikTokPublicShortIE()

    def fail_transport(*_args: object, **_kwargs: object) -> object:
        raise ExtractorError(
            "Unable to download webpage",
            cause=TransportError("connection reset"),
        )

    monkeypatch.setattr(extractor, "_request_webpage", fail_transport)

    with pytest.raises(
        ExtractorError,
        match="TikTok official player API temporarily unavailable",
    ) as captured:
        extractor._real_extract("https://vm.tiktok.com/ZTR45GpSF")

    assert captured.value.expected is True


def test_short_link_impossible_response_is_an_extractor_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = _TikTokPublicShortIE()
    monkeypatch.setattr(
        extractor,
        "_request_webpage",
        lambda *_args, **_kwargs: object(),
    )

    with pytest.raises(
        ExtractorError,
        match="TikTok official player response structure changed",
    ) as captured:
        extractor._real_extract("https://vm.tiktok.com/ZTR45GpSF")

    assert captured.value.expected is True


@pytest.mark.parametrize(
    "redirected",
    (
        "https://www.tiktok.com/@creator/photo/123",
        "https://www.tiktok.com/@creator/live",
        "https://www.tiktok.com/@creator",
        "https://example.com/video/123",
    ),
)
def test_short_link_rejects_non_video_redirect_without_generic_fallback(
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
) -> None:
    extractor = _TikTokPublicShortIE()
    response = type("Response", (), {"url": redirected})()
    monkeypatch.setattr(
        extractor,
        "_request_webpage",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(
        ExtractorError,
        match="TikTok video not available from the official player",
    ) as captured:
        extractor._real_extract("https://vm.tiktok.com/ZTR45GpSF")

    assert captured.value.expected is True
