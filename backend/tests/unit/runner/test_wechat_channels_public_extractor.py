from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.wechat_channels_public import (
    WechatChannelsPublicIE,
)
from app.runner.wechat_channels_policy import (
    allowed_media_url,
    has_protection_material,
    playable_parameters,
)
from yt_dlp.utils import ExtractorError

VIDEO_ID = "AFWYoXF5Bw"
SHARE_URL = f"https://weixin.qq.com/sph/{VIDEO_ID}"
MEDIA_URL = "https://finder.video.qq.com/251/20304/stodownload?encfilekey=public"


def feed_payload(
    *, video_url: str | None = None, decode_key: str = ""
) -> dict[str, Any]:
    feed: dict[str, Any] = {
        "description": "Public Channels video",
        "coverUrl": "https://wx.qpic.cn/cover.jpg",
    }
    if video_url is not None:
        feed["h264VideoInfo"] = {
            "videoUrl": video_url,
            "width": 1080,
            "height": 1920,
            "decodeKey": decode_key,
        }
    return {
        "errCode": 0,
        "data": {
            "authorInfo": {"nickname": "Public creator"},
            "feedInfo": feed,
        },
    }


def configured_extractor(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[object],
    *,
    authenticated: bool = True,
) -> tuple[WechatChannelsPublicIE, list[str]]:
    extractor = WechatChannelsPublicIE()
    requests: list[str] = []
    monkeypatch.setattr(extractor, "_download_webpage", lambda *args, **kwargs: "ok")

    def download_json(url: str, *args: object, **kwargs: object) -> object:
        requests.append(url)
        return responses.pop(0)

    monkeypatch.setattr(extractor, "_download_json", download_json)
    cookies = (
        {
            "hy_user": SimpleNamespace(value="operator-id"),
            "hy_token": SimpleNamespace(value="operator-token"),
        }
        if authenticated
        else {}
    )
    monkeypatch.setattr(extractor, "_get_cookies", lambda _url: cookies)
    return extractor, requests


def test_public_precheck_then_operator_session_extracts_clear_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor, requests = configured_extractor(
        monkeypatch,
        [
            feed_payload(),
            {
                "code": 0,
                "data": {
                    "playable_url": (
                        "https://channels.weixin.qq.com/finder-preview/pages/feed"
                        "?token=public-token&eid=export-id"
                    )
                },
            },
            feed_payload(video_url=MEDIA_URL),
        ],
    )

    info = extractor._real_extract(SHARE_URL)

    assert requests == [
        "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info",
        "https://yuanbao.tencent.com/api/weixin/get_parse_result",
        "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info",
    ]
    assert info["id"] == VIDEO_ID
    assert info["title"] == "Public Channels video"
    assert info["uploader"] == "Public creator"
    assert info["formats"][0]["url"] == MEDIA_URL
    assert info["formats"][0]["vcodec"] == "h264"


def test_anonymous_public_share_requests_isolated_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor, requests = configured_extractor(
        monkeypatch, [feed_payload()], authenticated=False
    )

    with pytest.raises(ExtractorError, match="Fresh cookies are needed"):
        extractor._real_extract(SHARE_URL)

    assert requests == [
        "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
    ]


def test_unavailable_public_share_never_uses_operator_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor, requests = configured_extractor(
        monkeypatch, [{"errCode": -1, "data": {}}]
    )

    with pytest.raises(ExtractorError, match="public link unavailable"):
        extractor._real_extract(SHARE_URL)

    assert len(requests) == 1


def test_rejects_invalid_resolver_output_and_protected_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid, _ = configured_extractor(
        monkeypatch,
        [feed_payload(), {"code": 0, "data": {"playable_url": "https://evil.test/"}}],
    )
    with pytest.raises(ExtractorError, match="cookies are no longer valid"):
        invalid._real_extract(SHARE_URL)

    protected, _ = configured_extractor(
        monkeypatch,
        [
            feed_payload(),
            {
                "code": 0,
                "data": {
                    "playable_url": (
                        "https://channels.weixin.qq.com/finder-preview/pages/feed"
                        "?token=t&eid=e"
                    )
                },
            },
            feed_payload(video_url=MEDIA_URL, decode_key="secret"),
        ],
    )
    with pytest.raises(ExtractorError, match="DRM protected"):
        protected._real_extract(SHARE_URL)


def test_parser_helpers_fail_closed() -> None:
    assert allowed_media_url(MEDIA_URL)
    assert not allowed_media_url(
        "https://finder.video.qq.com.evil.test/251/1/stodownload"
    )
    assert not allowed_media_url("http://finder.video.qq.com/251/1/stodownload")
    assert playable_parameters(
        {
            "playable_url": (
                "https://channels.weixin.qq.com/finder-preview/pages/feed"
                "?token=t&eid=e"
            )
        }
    ) == ("t", "e")
    assert playable_parameters(
        {
            "playable_url": (
                "https://channels.weixin.qq.com/finder-preview/pages/feed?token=t"
            )
        }
    ) is None
    assert has_protection_material({"data": {"decodeKey": "secret"}})
    assert not has_protection_material({"data": {"decodeKey": ""}})


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
            SHARE_URL,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert "WechatChannelsPublic" in result.stderr
    assert "Unsupported URL" not in result.stderr
